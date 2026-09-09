"""Calibrated multi-signal confidence scoring and verification status assignment."""

from typing import Any, Dict, List, Optional, Tuple

from xeren.plugins.verification.schemas import (
    CheckResult,
    JudgeVerdict,
    VerificationOperation,
    VerificationStatus,
)


class ConfidenceScorerTool:
    """Calibrates confidence scores across multiple signals and determines verification status."""

    def score(
        self,
        checks: List[CheckResult],
        judge_verdict: Optional[JudgeVerdict] = None,
        grounding_score: Optional[float] = None,
        consistency_score: Optional[float] = None,
        is_unverifiable: bool = False,
        confidence_threshold: float = 0.70,
        strict_mode: bool = False,
        operation: Optional[VerificationOperation] = None,
    ) -> Tuple[VerificationStatus, float, List[str], List[str]]:
        """
        Aggregate signals into calibrated confidence score and assign status.

        Returns:
            (status, confidence_score, failure_reasons, actionable_corrections)
        """
        failure_reasons: List[str] = []
        actionable_corrections: List[str] = []

        # 1. Unverifiable handling
        if is_unverifiable:
            for check in checks:
                if not check.passed and check.reason:
                    failure_reasons.append(check.reason)
                if check.actionable_correction:
                    actionable_corrections.append(check.actionable_correction)
            if not failure_reasons:
                failure_reasons.append("Verification could not proceed due to missing source evidence or ground truth.")
            if not actionable_corrections:
                actionable_corrections.append("Provide authoritative source evidence or retrieved documents.")
            return (
                VerificationStatus.UNVERIFIABLE,
                0.0,
                failure_reasons,
                actionable_corrections,
            )

        # 2. Extract check failures
        has_fatal_structural_failure = False
        fatal_check_names = {
            "null_check",
            "empty_string_check",
            "empty_collection_check",
            "python_syntax_check",
            "code_syntax_check",
            "schema_parsing_check",
            "schema_type_check",
        }

        for check in checks:
            if not check.passed:
                if check.name in fatal_check_names:
                    has_fatal_structural_failure = True
                if check.reason:
                    failure_reasons.append(check.reason)
                if check.actionable_correction:
                    actionable_corrections.append(check.actionable_correction)

        # 3. Incorporate judge failures
        if judge_verdict is not None:
            if not judge_verdict.is_valid:
                failure_reasons.append(f"Judge rejected candidate: {judge_verdict.rationale}")
            for imp in judge_verdict.suggested_improvements:
                if imp not in actionable_corrections:
                    actionable_corrections.append(imp)

        # 4. Multi-signal weighted calculation
        signal_weights: Dict[str, float] = {}
        signal_values: Dict[str, float] = {}

        # Checks signal
        if checks:
            check_avg = sum(c.score for c in checks) / len(checks)
            signal_weights["checks"] = 0.40
            signal_values["checks"] = check_avg

        # Grounding signal
        if grounding_score is not None:
            signal_weights["grounding"] = 0.30
            signal_values["grounding"] = grounding_score

        # Consistency signal
        if consistency_score is not None:
            signal_weights["consistency"] = 0.15
            signal_values["consistency"] = consistency_score

        # Judge signal
        if judge_verdict is not None:
            signal_weights["judge"] = 0.30
            signal_values["judge"] = judge_verdict.score

        if not signal_weights:
            composite_score = 1.0
        else:
            total_weight = sum(signal_weights.values())
            weighted_sum = sum(
                (weight / total_weight) * signal_values[name]
                for name, weight in signal_weights.items()
            )
            composite_score = weighted_sum

        # Penalize if fatal structural check failed
        if has_fatal_structural_failure:
            composite_score = min(composite_score, 0.25)

        composite_score = round(min(1.0, max(0.0, composite_score)), 3)

        # 5. Status assignment
        if has_fatal_structural_failure:
            status = VerificationStatus.FAILED
        elif strict_mode and (failure_reasons or composite_score < confidence_threshold):
            status = VerificationStatus.FAILED
        elif composite_score >= confidence_threshold and not any(not c.passed for c in checks):
            status = VerificationStatus.VERIFIED
        elif composite_score >= 0.40:
            status = VerificationStatus.PARTIALLY_VERIFIED
        else:
            status = VerificationStatus.FAILED

        return status, composite_score, failure_reasons, actionable_corrections
