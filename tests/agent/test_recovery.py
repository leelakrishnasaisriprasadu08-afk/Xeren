"""Tests for RecoveryManager fault tolerance, retry policies, and replanning."""

import pytest

from xeren.agent.recovery import RecoveryManager, RecoveryStrategy
from xeren.agent.types import ActionResult, AgentAction, BrowserObservation


def test_recovery_strategy_determination():
    """Verify appropriate strategies are selected based on error codes and retry count."""
    rm = RecoveryManager(max_retries=2)
    action = AgentAction(action_type="click", target="#submit")

    # 1. Timeout on first attempt -> RETRY
    timeout_res = ActionResult(
        action_id=action.action_id,
        success=False,
        error="Timed out",
        error_code="TIMEOUT",
        recoverable=True,
    )
    assert rm.determine_strategy(action, timeout_res) == RecoveryStrategy.RETRY

    # 2. Timeout on second attempt -> REFRESH_PAGE
    rm._retry_counts[f"{action.action_type}:{action.target}"] = 1
    assert rm.determine_strategy(action, timeout_res) == RecoveryStrategy.REFRESH_PAGE

    # 3. Non-recoverable error (e.g. security violation) -> FAIL
    unrec_res = ActionResult(
        action_id=action.action_id,
        success=False,
        error="Security violation",
        error_code="SECURITY_VIOLATION",
        recoverable=False,
    )
    assert rm.determine_strategy(action, unrec_res) == RecoveryStrategy.FAIL


def test_recovery_alternative_selector():
    """Verify alternative selector is selected when element is not found and alternatives exist."""
    rm = RecoveryManager()
    action = AgentAction(
        action_type="click",
        target="#primary-btn",
        parameters={"alternative_selectors": [".fallback-btn", "button[name='submit']"]},
    )
    not_found = ActionResult(
        action_id=action.action_id,
        success=False,
        error="Element not found",
        error_code="ELEMENT_NOT_FOUND",
        recoverable=True,
    )

    strategy = rm.determine_strategy(action, not_found)
    assert strategy == RecoveryStrategy.ALTERNATIVE_SELECTOR

    rec_action = rm.generate_recovery_action(action, strategy, not_found)
    assert rec_action is not None
    assert rec_action.target == ".fallback-btn"
    assert rec_action.metadata["is_recovery"] is True


def test_recovery_max_retries_exceeded_triggers_replan():
    """Verify that exceeding max retries triggers a replan strategy."""
    rm = RecoveryManager(max_retries=2)
    action = AgentAction(action_type="type", target="#input")
    fail_res = ActionResult(
        action_id=action.action_id,
        success=False,
        error="Typing failed",
        error_code="TYPE_FAILED",
        recoverable=True,
    )

    action_key = f"{action.action_type}:{action.target}"
    rm._retry_counts[action_key] = 2

    strategy = rm.determine_strategy(action, fail_res)
    assert strategy == RecoveryStrategy.REPLAN

    rm.reset()
    assert rm._retry_counts == {}
