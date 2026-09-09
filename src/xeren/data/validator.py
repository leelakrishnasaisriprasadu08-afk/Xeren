"""Validation and preprocessing for Xeren agent training and experience data."""

from typing import Dict, List, Optional, Set, Tuple
from pydantic import ValidationError

from xeren.data.schema import DatasetSplit, ExperienceRecord, ReviewStatus


class ValidationResult:
    """Result of dataset validation."""

    def __init__(self) -> None:
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.valid_count: int = 0
        self.duplicate_count: int = 0
        self.unverified_count: int = 0
        self.malformed_count: int = 0

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class DatasetValidator:
    """Validates experience records, enforces quality gates, and prevents data contamination."""

    def __init__(
        self,
        require_verified: bool = True,
        min_quality_score: float = 0.0,
        disallow_unverified: bool = True,
    ) -> None:
        self.require_verified = require_verified
        self.min_quality_score = min_quality_score
        self.disallow_unverified = disallow_unverified

    def preprocess_record(self, record: ExperienceRecord) -> ExperienceRecord:
        """Sanitize and normalize text in an experience record."""
        record.task = record.task.strip()
        record.plan = [p.strip() for p in record.plan if p.strip()]
        for action in record.actions:
            action.plan_step = action.plan_step.strip()
            action.tool_name = action.tool_name.strip()
            action.result = action.result.strip()
            if action.action_selection_rationale:
                action.action_selection_rationale = action.action_selection_rationale.strip()
            if action.error_message:
                action.error_message = action.error_message.strip()
            if action.correction:
                action.correction = action.correction.strip()
        for alt in record.alternatives:
            alt.candidate_action = alt.candidate_action.strip()
            alt.comparison_note = alt.comparison_note.strip()
            alt.rejected_reason = alt.rejected_reason.strip()
        for r in record.retrieval_items:
            r.source_id = r.source_id.strip()
            r.content = r.content.strip()
        return record

    def validate_record(self, record: ExperienceRecord) -> Tuple[bool, List[str]]:
        """Validate an individual experience record against quality requirements and logical consistency."""
        errors: List[str] = []

        if not record.sample_id or not record.sample_id.strip():
            errors.append("Sample ID cannot be empty.")

        if not record.task or not record.task.strip():
            errors.append("Task cannot be empty.")

        if self.require_verified and not record.is_verified:
            errors.append(f"Sample {record.sample_id} is unverified (is_verified=False).")

        if record.review_status == ReviewStatus.REJECTED:
            errors.append(f"Sample {record.sample_id} was marked as REJECTED during curation.")

        if record.final_quality_score < self.min_quality_score:
            errors.append(
                f"Sample {record.sample_id} quality score {record.final_quality_score} is below minimum {self.min_quality_score}."
            )

        if not record.verification.verifier:
            errors.append(f"Sample {record.sample_id} missing verifier name.")

        if not record.actions and not record.plan:
            errors.append(f"Sample {record.sample_id} contains neither a plan nor executed actions.")

        # Logical contradiction checks
        if record.success and record.failure_reason is not None:
            errors.append(
                f"Sample {record.sample_id} contradiction: marked success=True but failure_reason is present."
            )

        if not record.success and (not record.failure_reason or not record.failure_reason.strip()):
            errors.append(
                f"Sample {record.sample_id} contradiction: marked success=False but failure_reason is missing."
            )

        if record.success and not record.verification.verified:
            errors.append(
                f"Sample {record.sample_id} contradiction: marked success=True but verification.verified is False."
            )

        if record.verification.verified and record.verification.score < 0.5:
            errors.append(
                f"Sample {record.sample_id} contradiction: verification.verified is True but score {record.verification.score} is below 0.5."
            )

        # Action sequence and execution consistency
        if record.actions:
            for expected_idx, action in enumerate(record.actions):
                if action.step_index != expected_idx:
                    errors.append(
                        f"Sample {record.sample_id} has non-sequential action step_index: expected {expected_idx}, got {action.step_index}."
                    )
                    break

            if record.success and all(not a.success for a in record.actions):
                errors.append(
                    f"Sample {record.sample_id} contradiction: marked success=True but all action steps failed."
                )

        return len(errors) == 0, errors

    def validate_dataset(
        self,
        records: List[ExperienceRecord],
        enforce_split_separation: bool = True,
    ) -> ValidationResult:
        """Validate a collection of experience records, ensuring no duplicates or split leakage."""
        result = ValidationResult()
        seen_ids: Dict[str, Tuple[str, DatasetSplit]] = {}  # sample_id -> (sample_id, split)
        seen_fingerprints: Dict[str, Tuple[str, DatasetSplit]] = {}  # fingerprint -> (sample_id, split)

        for idx, raw_record in enumerate(records):
            record = self.preprocess_record(raw_record)
            is_valid, errors = self.validate_record(record)

            if not is_valid:
                for err in errors:
                    result.add_error(f"[Row {idx} / {record.sample_id}] {err}")
                if any("unverified" in e for e in errors):
                    result.unverified_count += 1
                else:
                    result.malformed_count += 1
                continue

            # Duplicate ID check
            if record.sample_id in seen_ids:
                prev_id, prev_split = seen_ids[record.sample_id]
                if enforce_split_separation and prev_split != record.split:
                    result.add_error(
                        f"Data leakage: {record.split.value} and {prev_split.value} share sample ID: {record.sample_id}"
                    )
                else:
                    result.add_error(f"Duplicate sample_id detected: {record.sample_id}")
                result.duplicate_count += 1
                continue
            seen_ids[record.sample_id] = (record.sample_id, record.split)

            # Duplicate content fingerprint check
            fp = record.content_fingerprint()
            if fp in seen_fingerprints:
                prev_id, prev_split = seen_fingerprints[fp]
                if enforce_split_separation and prev_split != record.split:
                    result.add_error(
                        f"Data leakage: {record.split.value} and {prev_split.value} share duplicate trajectory between {record.sample_id} and {prev_id}"
                    )
                else:
                    result.add_error(
                        f"Duplicate content trajectory detected between {record.sample_id} and {prev_id}."
                    )
                result.duplicate_count += 1
                continue
            seen_fingerprints[fp] = (record.sample_id, record.split)
            result.valid_count += 1

        return result
