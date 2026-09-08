"""Completion evaluator verifying task requirements, artifacts, and verification gates."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from xeren.agent.interfaces import CompletionEvaluation, CompletionEvaluator
from xeren.agent.state import TaskState

"""Evaluator assessing task completion, quality criteria, and termination conditions."""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from xeren.agent.types import AgentState
 main

logger = logging.getLogger("xeren.agent.evaluator")


 feature/core-architecture
class DefaultCompletionEvaluator(CompletionEvaluator):
    """Evaluates task completion against planned requirements, artifact presence, and verification gates.

    Never assumes the last action succeeding implies completion.
    """

    def __init__(
        self,
        required_artifact_keys: Optional[List[str]] = None,
        enforce_verification: bool = False,
    ) -> None:
        self.required_artifact_keys = required_artifact_keys or []
        self.enforce_verification = enforce_verification

    def evaluate(
        self,
        state: TaskState,
        verification_result: Optional[Any] = None,
    ) -> CompletionEvaluation:
        """Evaluate if the task requirements and quality gates have truly been satisfied."""
        satisfied: List[str] = []
        missing: List[str] = []

        logger.debug("Evaluating completion for task '%s' (goal: %s)", state.task_id, state.goal)

        # 1. Check Remaining Steps
        if state.remaining_steps:
            missing.append(f"{len(state.remaining_steps)} planned action(s) remain unexecuted")
        else:
            satisfied.append("All planned action steps have been processed")

        # 2. Check Completed Steps count
        if not state.completed_steps:
            missing.append("No actions have completed successfully")
        else:
            satisfied.append(f"{len(state.completed_steps)} action(s) completed successfully")

        # 3. Check Required Artifacts
        expected_artifacts = list(self.required_artifact_keys)
        # Also check if task metadata specified expected artifacts
        meta_artifacts = state.metadata.get("expected_artifacts", [])
        if isinstance(meta_artifacts, list):
            for a in meta_artifacts:
                if a not in expected_artifacts:
                    expected_artifacts.append(a)

        for art_key in expected_artifacts:
            # Check direct key or prefix match
            matched = any(k == art_key or k.startswith(f"{art_key}:") for k in state.artifacts.keys())
            if matched:
                satisfied.append(f"Required artifact '{art_key}' is present")
            else:
                missing.append(f"Required artifact '{art_key}' is missing from task state")

        # 4. Verification Gate Check
        if verification_result is not None:
            is_verified = False
            verif_score = 1.0

            # Inspect VerificationDetails or boolean or dict
            if hasattr(verification_result, "verified"):
                is_verified = bool(verification_result.verified)
                verif_score = getattr(verification_result, "score", 1.0)
            elif isinstance(verification_result, dict):
                is_verified = bool(verification_result.get("verified", False))
                verif_score = float(verification_result.get("score", 1.0))
            elif isinstance(verification_result, bool):
                is_verified = verification_result

            if is_verified:
                satisfied.append(f"Outcome verification PASSED (score: {verif_score})")
            else:
                missing.append(f"Outcome verification FAILED (score: {verif_score})")
        elif self.enforce_verification:
            missing.append("Verification is mandatory but was not performed")

        # 5. Determine Overall Completion Status
        is_complete = len(missing) == 0
        score = len(satisfied) / (len(satisfied) + len(missing)) if (satisfied or missing) else 0.0

        if is_complete:
            reason = f"All requirements and verification gates satisfied ({len(satisfied)} criteria met)."
        else:
            reason = f"Completion criteria not met: {'; '.join(missing)}"

        logger.info("Task completion evaluation: complete=%s, score=%.2f. Reason: %s", is_complete, score, reason)

        return CompletionEvaluation(
            is_complete=is_complete,
            confidence_score=round(score, 2),
            satisfied_requirements=satisfied,
            missing_requirements=missing,
            reason=reason,
        )


__all__ = ["DefaultCompletionEvaluator"]

class EvaluationResult(BaseModel):
    """Evaluation verdict on agent task progression."""

    is_complete: bool = Field(..., description="Whether task has reached terminal state")
    success: bool = Field(..., description="Whether task achieved user goal successfully")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence/quality score [0.0, 1.0]")
    reason: str = Field(default="", description="Explanation of evaluation judgment")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic metrics")


class Evaluator:
    """Evaluates agent execution state against termination criteria."""

    def __init__(self, max_steps: int = 20) -> None:
        self.max_steps = max_steps

    def evaluate(self, state: AgentState) -> EvaluationResult:
        """Assess whether the agent should terminate or continue executing."""
        # 1. Step budget overflow
        if state.step_count >= self.max_steps:
            return EvaluationResult(
                is_complete=True,
                success=False,
                score=0.0,
                reason=f"Exceeded maximum allowable steps ({self.max_steps}).",
                details={"step_count": state.step_count, "max_steps": self.max_steps},
            )

        # 2. Check if all plan steps were executed
        if state.plan and state.step_count >= len(state.plan):
            # Check if recent actions succeeded
            recent_results = [res for _, res in state.history[-len(state.plan):]]
            all_succeeded = all(r.success for r in recent_results)
            score = 1.0 if all_succeeded else 0.5

            return EvaluationResult(
                is_complete=True,
                success=all_succeeded,
                score=score,
                reason="All planned execution steps completed." if all_succeeded else "Plan finished with failures.",
                details={"executed_steps": state.step_count, "plan_length": len(state.plan)},
            )

        # 3. Check for non-recoverable failures in history
        if state.history:
            last_action, last_result = state.history[-1]
            if not last_result.success and not last_result.recoverable:
                return EvaluationResult(
                    is_complete=True,
                    success=False,
                    score=0.0,
                    reason=f"Unrecoverable error on action '{last_action.action_type}': {last_result.error}",
                    details={"error_code": last_result.error_code},
                )

        # Task ongoing
        return EvaluationResult(
            is_complete=False,
            success=False,
            score=0.5,
            reason="Task execution in progress.",
            details={"current_step": state.current_step, "step_count": state.step_count},
        )


__all__ = ["EvaluationResult", "Evaluator"]
 main
