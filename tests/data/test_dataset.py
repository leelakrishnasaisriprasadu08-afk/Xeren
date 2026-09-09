"""Unit tests for ExperienceDataset container and I/O."""

from pathlib import Path
import pytest

from xeren.data.dataset import ExperienceDataset, load_jsonl_dataset, save_jsonl_dataset
from xeren.data.schema import (
    ActionStep,
    DatasetSplit,
    ExperienceRecord,
    VerificationDetails,
)


def _make_record(sample_id: str, split: DatasetSplit = DatasetSplit.TRAIN, task: str = "Test") -> ExperienceRecord:
    return ExperienceRecord(
        sample_id=sample_id,
        task=task,
        plan=["Execute action"],
        actions=[
            ActionStep(
                step_index=0,
                plan_step="Execute action",
                tool_name="tool_a",
                tool_args={"p": sample_id},
                result=f"Result for {sample_id}",
                success=True,
            )
        ],
        prediction_confidence=0.9,
        verification=VerificationDetails(
            verified=True,
            verifier="test_verifier",
            score=0.95,
            details={},
        ),
        success=True,
        final_quality_score=0.95,
        split=split,
        is_verified=True,
    )


def test_dataset_add_and_get() -> None:
    ds = ExperienceDataset()
    r1 = _make_record("s1", DatasetSplit.TRAIN)
    r2 = _make_record("s2", DatasetSplit.VAL)
    ds.add(r1)
    ds.add(r2)

    assert len(ds) == 2
    assert ds.get("s1") == r1
    assert ds.get("s2") == r2
    assert ds.get("non-existent") is None


def test_dataset_prevent_duplicates() -> None:
    ds = ExperienceDataset()
    r1 = _make_record("s1")
    ds.add(r1)

    # Same ID
    with pytest.raises(ValueError, match="Duplicate sample_id rejected"):
        ds.add(r1)


def test_dataset_split_filtering() -> None:
    ds = ExperienceDataset([
        _make_record("s1", DatasetSplit.TRAIN),
        _make_record("s2", DatasetSplit.TRAIN),
        _make_record("s3", DatasetSplit.VAL),
        _make_record("s4", DatasetSplit.TEST),
    ])

    train_ds = ds.get_split(DatasetSplit.TRAIN)
    val_ds = ds.get_split("val")
    test_ds = ds.get_split(DatasetSplit.TEST)

    assert len(train_ds) == 2
    assert len(val_ds) == 1
    assert len(test_ds) == 1


def test_dataset_jsonl_roundtrip(tmp_path: Path) -> None:
    file_path = tmp_path / "test_exp.jsonl"
    ds = ExperienceDataset([
        _make_record("s1", DatasetSplit.TRAIN, "Task 1"),
        _make_record("s2", DatasetSplit.VAL, "Task 2"),
    ])

    count = save_jsonl_dataset(ds, file_path)
    assert count == 2
    assert file_path.exists()

    loaded = load_jsonl_dataset(file_path, enforce_verified=True)
    assert len(loaded) == 2
    assert loaded.get("s1") is not None
    assert loaded.get("s2") is not None


def test_dataset_remove() -> None:
    ds = ExperienceDataset()
    r1 = _make_record("s1")
    ds.add(r1)
    assert len(ds) == 1
    assert ds.remove("s1") is True
    assert len(ds) == 0
    assert ds.remove("s1") is False


def test_dataset_deduplicate() -> None:
    ds = ExperienceDataset()
    r1 = _make_record("s1", task="Identical task")
    r2 = _make_record("s2", task="Different task")
    ds.add(r1)
    ds.add(r2)

    # Directly insert a duplicate record bypassing add validation
    r_dup = _make_record("s3", task="Identical task")
    r_dup.actions = r1.actions
    ds._records["s3"] = r_dup

    assert len(ds) == 3
    removed = ds.deduplicate()
    assert removed == 1
    assert len(ds) == 2
    assert "s3" not in ds._records


def test_dataset_filter_for_training() -> None:
    ds = ExperienceDataset()
    r_good = _make_record("good", task="T1")
    r_unver = _make_record("unver", task="T2")
    r_unver.is_verified = False

    r_fail = _make_record("fail", task="T3")
    r_fail.success = False
    r_fail.failure_reason = "Intentional fail"

    ds.add(r_good)
    ds.add(r_unver, enforce_verified=False)
    ds.add(r_fail)

    eligible = ds.filter_for_training(require_verified=True, allow_failures=False)
    assert len(eligible) == 1
    assert eligible.get("good") is not None
    assert eligible.get("unver") is None
    assert eligible.get("fail") is None


def test_dataset_split_train_val_test() -> None:
    ds = ExperienceDataset()
    for i in range(10):
        ds.add(_make_record(f"s{i:02d}", task=f"Unique task {i}"))

    train_ds, val_ds, test_ds = ds.split_train_val_test(
        train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42
    )

    assert len(train_ds) == 8
    assert len(val_ds) == 1
    assert len(test_ds) == 1
    assert len(train_ds) + len(val_ds) + len(test_ds) == 10

    # Verify zero leakage across splits
    train_ids = set(r.sample_id for r in train_ds.records)
    val_ids = set(r.sample_id for r in val_ds.records)
    test_ids = set(r.sample_id for r in test_ds.records)

    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)

    # Verify split field set on records
    for r in train_ds.records:
        assert r.split == DatasetSplit.TRAIN
    for r in val_ds.records:
        assert r.split == DatasetSplit.VAL
    for r in test_ds.records:
        assert r.split == DatasetSplit.TEST


def test_dataset_summary_stats() -> None:
    ds = ExperienceDataset()
    ds.add(_make_record("s1", DatasetSplit.TRAIN, "T1"))
    ds.add(_make_record("s2", DatasetSplit.VAL, "T2"))

    stats = ds.summary_stats()
    assert stats["total_records"] == 2
    assert stats["splits"]["train"] == 1
    assert stats["splits"]["val"] == 1
    assert stats["success_count"] == 2
    assert stats["failure_count"] == 0
    assert stats["verified_count"] == 2
    assert stats["avg_quality_score"] > 0
    assert stats["total_actions"] == 2
