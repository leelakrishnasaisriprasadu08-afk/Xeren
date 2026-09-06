"""Evaluator assessing task completion, quality criteria, and termination conditions."""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from xeren.agent.types import AgentState

logger = logging.getLogger("xeren.agent.evaluator")


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
