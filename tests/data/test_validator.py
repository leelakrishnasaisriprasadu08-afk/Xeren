"""Unit tests for DatasetValidator and preprocessing."""

from xeren.data.schema import (
    ActionStep,
    DatasetSplit,
    ExperienceRecord,
    ReviewStatus,
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


def test_validator_detects_logical_contradictions() -> None:
    validator = DatasetValidator()

    # 1. success=True with failure_reason
    rec_c1 = _make_valid_record("c1")
    rec_c1.failure_reason = "Spurious error"
    valid, errors = validator.validate_record(rec_c1)
    assert valid is False
    assert any("marked success=True but failure_reason is present" in e for e in errors)

    # 2. success=False without failure_reason
    rec_c2 = _make_valid_record("c2")
    rec_c2.success = False
    rec_c2.failure_reason = None
    valid, errors = validator.validate_record(rec_c2)
    assert valid is False
    assert any("marked success=False but failure_reason is missing" in e for e in errors)

    # 3. success=True but verification failed
    rec_c3 = _make_valid_record("c3")
    rec_c3.verification.verified = False
    valid, errors = validator.validate_record(rec_c3)
    assert valid is False
    assert any("verification.verified is False" in e for e in errors)

    # 4. verification verified=True but score < 0.5
    rec_c4 = _make_valid_record("c4")
    rec_c4.verification.score = 0.2
    valid, errors = validator.validate_record(rec_c4)
    assert valid is False
    assert any("score 0.2 is below 0.5" in e for e in errors)

    # 5. Non-sequential action steps
    rec_c5 = _make_valid_record("c5")
    rec_c5.actions = [
        ActionStep(step_index=1, plan_step="Step", tool_name="t", result="r"),  # expected 0
    ]
    valid, errors = validator.validate_record(rec_c5)
    assert valid is False
    assert any("non-sequential action step_index" in e for e in errors)

    # 6. All actions failed while marked success=True
    rec_c6 = _make_valid_record("c6")
    rec_c6.actions = [
        ActionStep(step_index=0, plan_step="S0", tool_name="t", result="Fail", success=False),
        ActionStep(step_index=1, plan_step="S1", tool_name="t", result="Fail 2", success=False),
    ]
    valid, errors = validator.validate_record(rec_c6)
    assert valid is False
    assert any("all action steps failed" in e for e in errors)

    # 7. Rejected review status
    rec_c7 = _make_valid_record("c7")
    rec_c7.review_status = ReviewStatus.REJECTED
    valid, errors = validator.validate_record(rec_c7)
    assert valid is False
    assert any("marked as REJECTED" in e for e in errors)
