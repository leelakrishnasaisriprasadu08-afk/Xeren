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
