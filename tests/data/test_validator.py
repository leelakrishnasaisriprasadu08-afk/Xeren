"""Unit tests for DatasetValidator and preprocessing."""

from xeren.data.schema import (
    ActionStep,
    DatasetSplit,
    ExperienceRecord,
    VerificationDetails,
)
from xeren.data.validator import DatasetValidator


def _make_valid_record(sample_id: str = "exp-val-01", split: DatasetSplit = DatasetSplit.TRAIN, task: str = "Sample task") -> ExperienceRecord:
    return ExperienceRecord(
        sample_id=sample_id,
        task=task,
        plan=["Execute action"],
        actions=[
            ActionStep(
                step_index=0,
                plan_step="Execute action",
                tool_name="test_tool",
                tool_args={"key": "val"},
                result="Success output",
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
        final_quality_score=0.9,
        split=split,
        is_verified=True,
    )


def test_validator_accepts_clean_dataset() -> None:
    validator = DatasetValidator(require_verified=True)
    r1 = _make_valid_record("s1", DatasetSplit.TRAIN, "Task 1")
    r2 = _make_valid_record("s2", DatasetSplit.VAL, "Task 2")
    r3 = _make_valid_record("s3", DatasetSplit.TEST, "Task 3")

    result = validator.validate_dataset([r1, r2, r3])
    assert result.is_valid is True
    assert result.valid_count == 3
    assert len(result.errors) == 0


def test_validator_rejects_unverified_records() -> None:
    validator = DatasetValidator(require_verified=True)
    rec = _make_valid_record("s1", DatasetSplit.TRAIN)
    rec.is_verified = False

    result = validator.validate_dataset([rec])
    assert result.is_valid is False
    assert result.unverified_count == 1
    assert any("unverified" in e for e in result.errors)


def test_validator_detects_duplicate_ids() -> None:
    validator = DatasetValidator()
    r1 = _make_valid_record("same-id", DatasetSplit.TRAIN, "Task A")
    r2 = _make_valid_record("same-id", DatasetSplit.TRAIN, "Task B")

    result = validator.validate_dataset([r1, r2])
    assert result.is_valid is False
    assert result.duplicate_count == 1
    assert any("Duplicate sample_id detected" in e for e in result.errors)


def test_validator_detects_duplicate_content_trajectories() -> None:
    validator = DatasetValidator()
    r1 = _make_valid_record("s1", DatasetSplit.TRAIN, "Identical Task")
    r2 = _make_valid_record("s2", DatasetSplit.TRAIN, "Identical Task")  # Same task and actions

    result = validator.validate_dataset([r1, r2])
    assert result.is_valid is False
    assert result.duplicate_count == 1
    assert any("Duplicate content trajectory detected" in e for e in result.errors)


def test_validator_detects_cross_split_leakage() -> None:
    validator = DatasetValidator()
    r1 = _make_valid_record("s1", DatasetSplit.TRAIN, "Task Leak")
    r2 = _make_valid_record("s2", DatasetSplit.TEST, "Task Leak")  # Shared trajectory across train and test

    result = validator.validate_dataset([r1, r2], enforce_split_separation=True)
    assert result.is_valid is False
    assert any("Data leakage" in e for e in result.errors)
