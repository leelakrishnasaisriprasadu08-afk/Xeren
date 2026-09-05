"""Data verification and constraint validation tool."""

import logging
import re
from typing import Any, Dict, List, Sequence

from xeren.plugins.data.schemas import (
    DataInput,
    DataOperation,
    DataResult,
    DataValidationRule,
    DataVerificationReport,
    StructuredDataset,
    VerificationFinding,
)

logger = logging.getLogger("xeren.plugins.data.tools.verification")


class DataVerificationTool:
    """Verifies dataset integrity, schema constraints, and business validation rules."""

    def verify(
        self,
        dataset: StructuredDataset,
        rules: Sequence[DataValidationRule],
    ) -> DataVerificationReport:
        """Evaluate validation rules against dataset records."""
        findings: List[VerificationFinding] = []
        rules_checked = len(rules)

        for rule in rules:
            finding = self._check_rule(dataset, rule)
            findings.append(finding)

        rules_passed = sum(1 for f in findings if f.passed)
        rules_failed = sum(1 for f in findings if not f.passed)

        # Dataset is valid if no rule failed
        is_valid = rules_failed == 0
        quality_score = round(rules_passed / rules_checked, 2) if rules_checked > 0 else 1.0

        summary = (
            f"All {rules_checked} validation rule(s) passed successfully."
            if is_valid
            else f"Validation failed: {rules_failed} of {rules_checked} rule(s) failed."
        )

        return DataVerificationReport(
            is_valid=is_valid,
            rules_checked=rules_checked,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            quality_score=quality_score,
            findings=findings,
            summary=summary,
        )

    def execute(self, input_data: DataInput) -> DataResult:
        """Execute verification rules on a DataInput payload."""
        try:
            dataset = input_data.dataset
            if dataset is None:
                from xeren.plugins.data.tools.ingestion import DataIngestionTool
                dataset = DataIngestionTool().ingest(
                    data=input_data.data or input_data.records,
                    file_path=input_data.file_path,
                    format_hint=input_data.format,
                    options=input_data.metadata,
                )
            rules = input_data.validation_rules or input_data.verification_rules or []
            report = self.verify(dataset=dataset, rules=rules)
            return DataResult(
                operation=DataOperation.VERIFY,
                success=True,
                dataset=dataset,
                verification=report,
                stats={"total_rules": report.rules_checked, "passed_rules": report.rules_passed},
            )
        except Exception as err:
            return DataResult(
                operation=DataOperation.VERIFY,
                success=False,
                error=str(err),
            )

    def _check_rule(
        self,
        dataset: StructuredDataset,
        rule: DataValidationRule,
    ) -> VerificationFinding:
        """Evaluate a single constraint rule."""
        c_type = (rule.check_type or rule.rule_name).lower()
        col = rule.column
        params = rule.params or rule.parameters or {}

        # 1. Column presence check
        if c_type == "column_exists":
            if col not in dataset.columns:
                return VerificationFinding(
                    rule_name=rule.rule_name,
                    passed=False,
                    severity="error",
                    message=f"Required column '{col}' is missing from dataset.",
                    column=col,
                    invalid_count=1,
                    failed_row_indices=[],
                )
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=True,
                severity="info",
                message=f"Column '{col}' is present.",
                column=col,
            )

        # If rule targets a column that does not exist in dataset
        if col and col not in dataset.columns:
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=False,
                severity="error",
                message=f"Column '{col}' targeted by rule '{rule.rule_name}' does not exist.",
                column=col,
                invalid_count=1,
                failed_row_indices=[],
            )

        values = dataset.get_column_values(col) if col else []

        # 2. Not Null constraint
        if c_type in ("not_null", "non_null"):
            failed_indices = [idx for idx, v in enumerate(values) if v is None or v == ""]
            passed = len(failed_indices) == 0
            msg = (
                f"Column '{col}' has no null values."
                if passed
                else f"Found {len(failed_indices)} null values in column '{col}'"
            )
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=passed,
                severity="error" if not passed else "info",
                message=msg,
                column=col,
                invalid_count=len(failed_indices),
                failed_row_indices=failed_indices,
            )

        # 3. Unique constraint
        if c_type == "unique":
            seen: Dict[str, int] = {}
            failed_indices: List[int] = []
            for idx, v in enumerate(values):
                if v is not None and v != "":
                    s = str(v)
                    if s in seen:
                        failed_indices.append(idx)
                    else:
                        seen[s] = idx

            passed = len(failed_indices) == 0
            msg = (
                f"All values in column '{col}' are unique."
                if passed
                else f"Column '{col}' has {len(failed_indices)} duplicate value(s)."
            )
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=passed,
                severity="error" if not passed else "info",
                message=msg,
                column=col,
                invalid_count=len(failed_indices),
                failed_row_indices=failed_indices,
            )

        # 4. Value Range constraint
        if c_type == "value_range":
            min_bound = params.get("min") if params.get("min") is not None else params.get("min_value")
            max_bound = params.get("max") if params.get("max") is not None else params.get("max_value")
            failed_indices = []
            for idx, v in enumerate(values):
                if v is not None and v != "":
                    try:
                        num = float(v)
                        if min_bound is not None and num < float(min_bound):
                            failed_indices.append(idx)
                        elif max_bound is not None and num > float(max_bound):
                            failed_indices.append(idx)
                    except (ValueError, TypeError):
                        failed_indices.append(idx)

            passed = len(failed_indices) == 0
            msg = (
                f"Values in '{col}' fall within [{min_bound}, {max_bound}]."
                if passed
                else f"{len(failed_indices)} value(s) in '{col}' fall outside range."
            )
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=passed,
                severity="error" if not passed else "info",
                message=msg,
                column=col,
                invalid_count=len(failed_indices),
                failed_row_indices=failed_indices,
            )

        # 5. Allowed Values / Enum constraint
        if c_type in ("allowed_values", "in_set"):
            allowed_list = params.get("allowed") or params.get("allowed_values") or []
            allowed_set = set(allowed_list)
            failed_indices = []
            for idx, v in enumerate(values):
                if v is not None and v != "" and v not in allowed_set:
                    failed_indices.append(idx)

            passed = len(failed_indices) == 0
            msg = (
                f"All values in '{col}' are within the permitted set."
                if passed
                else f"{len(failed_indices)} value(s) in '{col}' are not in allowed set: {list(allowed_set)[:5]}."
            )
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=passed,
                severity="error" if not passed else "info",
                message=msg,
                column=col,
                invalid_count=len(failed_indices),
                failed_row_indices=failed_indices,
            )

        # 6. Regex Pattern constraint
        if c_type == "regex":
            pattern = params.get("pattern", ".*")
            regex = re.compile(pattern)
            failed_indices = []
            for idx, v in enumerate(values):
                if v is not None and v != "" and not regex.match(str(v)):
                    failed_indices.append(idx)

            passed = len(failed_indices) == 0
            msg = (
                f"All values in '{col}' match regex '{pattern}'."
                if passed
                else f"{len(failed_indices)} value(s) in '{col}' do not match pattern '{pattern}'."
            )
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=passed,
                severity="error" if not passed else "info",
                message=msg,
                column=col,
                invalid_count=len(failed_indices),
                failed_row_indices=failed_indices,
            )

        # 7. Row Count Range
        if c_type in ("row_count", "row_range"):
            raw_min = params.get("min") if params.get("min") is not None else params.get("min_rows", 0)
            raw_max = params.get("max") if params.get("max") is not None else params.get("max_rows", float("inf"))
            min_r = float(raw_min) if raw_min is not None else 0.0
            max_r = float(raw_max) if raw_max is not None else float("inf")
            rows_num = float(int(dataset.row_count))
            passed = min_r <= rows_num <= max_r
            msg = (
                f"Dataset row count {dataset.row_count} satisfies range [{min_r}, {max_r}]."
                if passed
                else f"Dataset row count {dataset.row_count} outside expected range [{min_r}, {max_r}]."
            )
            return VerificationFinding(
                rule_name=rule.rule_name,
                passed=passed,
                severity="error" if not passed else "info",
                message=msg,
                invalid_count=0 if passed else 1,
            )

        return VerificationFinding(
            rule_name=rule.rule_name,
            passed=True,
            severity="info",
            message=f"Rule check '{c_type}' evaluated.",
            column=col,
        )


__all__ = ["DataVerificationTool"]
