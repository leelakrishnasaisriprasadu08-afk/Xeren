"""Failure recovery, bounded retries, and loop prevention for the Autonomous Work Agent."""

from __future__ import annotations

import logging
from typing import Dict, Optional

from xeren.agent.actions import Action, ActionResult
from xeren.agent.interfaces import (
    FailureCategory,
    FailureClassification,
    RecoveryDecision,
    RecoveryManager,
)
from xeren.agent.state import TaskState

"""Recovery Manager providing automated fault tolerance, retry, and replanning strategies."""

from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

from xeren.agent.types import ActionResult, AgentAction
 main

logger = logging.getLogger("xeren.agent.recovery")


 feature/core-architecture
class DefaultRecoveryManager(RecoveryManager):
    """Manages failure classification, bounded retries, loop prevention, and replan decisions."""

    def __init__(
        self,
        max_step_retries: int = 3,
        max_replans: int = 3,
        max_total_cycles: int = 50,
    ) -> None:
        self.max_step_retries = max_step_retries
        self.max_replans = max_replans
        self.max_total_cycles = max_total_cycles

        # Internal tracking per task: action_id or fingerprint -> retry count
        self._action_retries: Dict[str, int] = {}
        self._replan_count: int = 0
        self._stagnation_history: Dict[str, int] = {}

    def classify_failure(
        self,
        action: Action,
        result: ActionResult,
        state: TaskState,
    ) -> FailureClassification:
        """Classify the failure into category, severity, and retryability."""
        err_msg = (result.error or "").lower()
        err_type = result.metadata.get("error_type", "")

        # 1. Permission Denied
        if "permission" in err_msg or "approval" in err_msg or "not authorized" in err_msg:
            return FailureClassification(
                category=FailureCategory.PERMISSION_DENIED,
                retryable=False,
                suggestion="Action requires explicit approval or authorization.",
                details={"error": result.error},
            )

        # 2. Timeout
        if "timeout" in err_msg or err_type == "PluginTimeoutError":
            return FailureClassification(
                category=FailureCategory.TIMEOUT,
                retryable=True,
                suggestion="Execution timed out; retry with extended timeout or backoff.",
                details={"error": result.error},
            )

        # 3. Validation Error
        if "validation" in err_msg or err_type == "PluginValidationError":
            return FailureClassification(
                category=FailureCategory.VALIDATION_ERROR,
                retryable=False,  # Same invalid input will fail again; replan instead
                suggestion="Input failed schema validation; replan with corrected schema.",
                details={"error": result.error},
            )

        # 4. Plugin Error (Not Found / Unregistered)
        if "not registered" in err_msg or err_type == "PluginNotFoundError":
            return FailureClassification(
                category=FailureCategory.PLUGIN_ERROR,
                retryable=False,  # Retrying non-existent plugin won't help; replan
                suggestion="Plugin is not registered; replan using an available alternative target.",
                details={"error": result.error},
            )

        # 5. Transient Network / Rate Limit Errors
        transient_indicators = ["transient", "connection reset", "503", "429", "rate limit", "busy", "temporary"]
        if any(ind in err_msg for ind in transient_indicators):
            return FailureClassification(
                category=FailureCategory.TRANSIENT,
                retryable=True,
                suggestion="Transient issue detected; safe to retry with backoff.",
                details={"error": result.error},
            )

        # 6. Fatal Unrecoverable Errors
        fatal_indicators = ["segmentation fault", "out of memory", "critical security violation"]
        if any(ind in err_msg for ind in fatal_indicators):
            return FailureClassification(
                category=FailureCategory.FATAL,
                retryable=False,
                suggestion="Fatal unrecoverable error encountered.",
                details={"error": result.error},
            )

        # 7. Generic Plugin Execution Error
        if err_type == "PluginExecutionError" or "failed" in err_msg:
            return FailureClassification(
                category=FailureCategory.PLUGIN_ERROR,
                retryable=True,
                suggestion="Plugin execution error; attempt retry or alternative parameters.",
                details={"error": result.error},
            )

        return FailureClassification(
            category=FailureCategory.UNKNOWN,
            retryable=True,
            suggestion="Unknown failure; attempt bounded retry.",
            details={"error": result.error},
        )

    def can_retry(self, action: Action, state: TaskState) -> bool:
        """Check whether the action has remaining retries within configured bounds."""
        key = action.action_id
        retries = self._action_retries.get(key, 0)
        return retries < self.max_step_retries

    def handle_failure(
        self,
        action: Action,
        result: ActionResult,
        state: TaskState,
    ) -> str:
        """Evaluate failure and determine next recovery action."""
        classification = self.classify_failure(action, result, state)
        action_key = action.action_id
        fingerprint = action.fingerprint()

        # Update retry and stagnation counters
        self._action_retries[action_key] = self._action_retries.get(action_key, 0) + 1
        self._stagnation_history[fingerprint] = self._stagnation_history.get(fingerprint, 0) + 1
        current_retries = self._action_retries[action_key]
        stagnation_count = self._stagnation_history[fingerprint]

        logger.warning(
            "Action '%s' failed (attempt %d/%d, fingerprint failure count: %d, category: %s). Error: %s",
            action_key,
            current_retries,
            self.max_step_retries,
            stagnation_count,
            classification.category,
            result.error,
        )

        # 1. Total cycle bound check
        if state.attempt_count >= self.max_total_cycles:
            logger.error("Max total execution cycles (%d) exceeded. Halting task safely.", self.max_total_cycles)
            return RecoveryDecision.FAIL

        # 2. Permission Denied -> Wait approval or fail
        if classification.category == FailureCategory.PERMISSION_DENIED:
            return RecoveryDecision.WAIT_APPROVAL

        # 3. Fatal error -> Fail immediately
        if classification.category == FailureCategory.FATAL:
            logger.error("Fatal error detected for action '%s'. Failing safely.", action_key)
            return RecoveryDecision.FAIL

        # 4. Stagnation / Infinite-loop prevention
        # If the exact same action has failed multiple times even across replans
        if stagnation_count > (self.max_step_retries * 2):
            logger.error("Stagnation detected: identical action payload has failed %d times. Failing safely.", stagnation_count)
            return RecoveryDecision.FAIL

        # 5. Bounded Retry for retryable failures
        if classification.retryable and current_retries <= self.max_step_retries:
            logger.info("Retrying action '%s' (retry %d of %d)", action_key, current_retries, self.max_step_retries)
            return RecoveryDecision.RETRY

        # 6. Replan if retries exhausted and replan quota remains
        if self._replan_count < self.max_replans:
            self._replan_count += 1
            logger.info("Retries exhausted for '%s'. Triggering replan (%d of %d)", action_key, self._replan_count, self.max_replans)
            return RecoveryDecision.REPLAN

        # 7. Retries and replans both exhausted -> Fail safely
        logger.error(
            "Retries (%d) and replan attempts (%d) exhausted for action '%s'. Safe termination.",
            self.max_step_retries,
            self.max_replans,
            action_key,
        )
        return RecoveryDecision.FAIL

    def reset(self) -> None:
        """Reset internal tracking counters for a fresh task."""
        self._action_retries.clear()
        self._replan_count = 0
        self._stagnation_history.clear()


__all__ = ["DefaultRecoveryManager"]

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
 main
