"""Recovery Manager providing automated fault tolerance, retry, and replanning strategies."""

from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

from xeren.agent.types import ActionResult, AgentAction

logger = logging.getLogger("xeren.agent.recovery")


class RecoveryStrategy(str, Enum):
    """Strategies to resolve execution failures."""

    RETRY = "retry"
    REFRESH_PAGE = "refresh_page"
    ALTERNATIVE_SELECTOR = "alternative_selector"
    REPLAN = "replan"
    FALLBACK_ACTION = "fallback_action"
    ESCALATE_TO_USER = "escalate_to_user"
    FAIL = "fail"


class RecoveryManager:
    """Evaluates failed action results and formulates recovery actions."""

    def __init__(
        self,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._retry_counts: Dict[str, int] = {}

    def determine_strategy(
        self,
        action: AgentAction,
        result: ActionResult,
    ) -> RecoveryStrategy:
        """Analyze failure context and decide optimal recovery strategy."""
        if result.success:
            return RecoveryStrategy.RETRY

        # Non-recoverable failures (e.g. security violations, authentication rejections)
        if not result.recoverable:
            return RecoveryStrategy.FAIL

        action_key = f"{action.action_type}:{action.target}"
        current_retries = self._retry_counts.get(action_key, 0)

        if current_retries >= self.max_retries:
            logger.warning("Action %s exceeded max retries (%d). Triggering replan.", action_key, self.max_retries)
            return RecoveryStrategy.REPLAN

        error_code = (result.error_code or "").upper()

        if error_code == "TIMEOUT":
            # Timeouts benefit from retry or refresh
            if current_retries == 0:
                return RecoveryStrategy.RETRY
            return RecoveryStrategy.REFRESH_PAGE

        if error_code == "ELEMENT_NOT_FOUND":
            # Missing element: check if alternative selector exists, otherwise replan
            alternatives = action.parameters.get("alternative_selectors", [])
            if alternatives and current_retries < len(alternatives):
                return RecoveryStrategy.ALTERNATIVE_SELECTOR
            return RecoveryStrategy.REPLAN

        if error_code in {"NETWORK_ERROR", "NAVIGATION_FAILED"}:
            return RecoveryStrategy.RETRY

        return RecoveryStrategy.RETRY

    def generate_recovery_action(
        self,
        action: AgentAction,
        strategy: RecoveryStrategy,
        result: ActionResult,
    ) -> Optional[AgentAction]:
        """Formulate next action according to chosen recovery strategy."""
        action_key = f"{action.action_type}:{action.target}"
        self._retry_counts[action_key] = self._retry_counts.get(action_key, 0) + 1

        if strategy == RecoveryStrategy.RETRY:
            # Re-issue original action with updated action_id
            return AgentAction(
                action_id=str(uuid.uuid4()),
                action_type=action.action_type,
                target=action.target,
                parameters=dict(action.parameters),
                requires_approval=action.requires_approval,
                consequential=action.consequential,
                description=f"Retry: {action.description or action.action_type}",
                metadata={"is_recovery": True, "recovery_strategy": strategy.value},
            )

        if strategy == RecoveryStrategy.REFRESH_PAGE:
            return AgentAction(
                action_id=str(uuid.uuid4()),
                action_type="navigate",
                target=result.observation.url if result.observation else action.target,
                parameters={"refresh": True},
                description="Refresh page to recover from state desynchronization",
                metadata={"is_recovery": True, "recovery_strategy": strategy.value},
            )

        if strategy == RecoveryStrategy.ALTERNATIVE_SELECTOR:
            alternatives: List[str] = action.parameters.get("alternative_selectors", [])
            idx = self._retry_counts[action_key] - 1
            if idx < len(alternatives):
                new_target = alternatives[idx]
                return AgentAction(
                    action_id=str(uuid.uuid4()),
                    action_type=action.action_type,
                    target=new_target,
                    parameters=dict(action.parameters),
                    description=f"Try alternative selector '{new_target}'",
                    metadata={"is_recovery": True, "recovery_strategy": strategy.value},
                )

        return None

    def reset(self) -> None:
        """Reset retry tracking state."""
        self._retry_counts.clear()


__all__ = ["RecoveryStrategy", "RecoveryManager"]
