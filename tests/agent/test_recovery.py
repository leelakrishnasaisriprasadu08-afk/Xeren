 feature/core-architecture
"""Tests for DefaultRecoveryManager failure classification, bounded retries, and loop prevention."""

import pytest

from xeren.agent.actions import Action, ActionResult
from xeren.agent.interfaces import FailureCategory, RecoveryDecision
from xeren.agent.recovery import DefaultRecoveryManager
from xeren.agent.state import TaskState


def test_failure_classification_categories():
    """Verify accurate failure classification for diverse error types."""
    rm = DefaultRecoveryManager()
    state = TaskState(goal="Test")
    act = Action(target="test", parameters={})

    # Permission denied
    res_perm = ActionResult(action_id=act.action_id, success=False, error="Action requires approval")
    cls_perm = rm.classify_failure(act, res_perm, state)
    assert cls_perm.category == FailureCategory.PERMISSION_DENIED
    assert cls_perm.retryable is False

    # Timeout
    res_to = ActionResult(action_id=act.action_id, success=False, error="Connection timeout after 30s")
    cls_to = rm.classify_failure(act, res_to, state)
    assert cls_to.category == FailureCategory.TIMEOUT
    assert cls_to.retryable is True

    # Validation Error
    res_val = ActionResult(action_id=act.action_id, success=False, error="Validation error: missing field")
    cls_val = rm.classify_failure(act, res_val, state)
    assert cls_val.category == FailureCategory.VALIDATION_ERROR
    assert cls_val.retryable is False

    # Fatal error
    res_fatal = ActionResult(action_id=act.action_id, success=False, error="Critical segmentation fault")
    cls_fatal = rm.classify_failure(act, res_fatal, state)
    assert cls_fatal.category == FailureCategory.FATAL
    assert cls_fatal.retryable is False


def test_bounded_retries_and_replan():
    """Verify recovery manager allows retries up to limit then triggers replan."""
    rm = DefaultRecoveryManager(max_step_retries=2, max_replans=1)
    state = TaskState(goal="Test bounded retry")
    act = Action(action_id="act-1", target="coding", parameters={"task": "test"})
    res_fail = ActionResult(action_id="act-1", success=False, error="Transient network glitch")

    # Attempt 1 -> RETRY
    d1 = rm.handle_failure(act, res_fail, state)
    assert d1 == RecoveryDecision.RETRY

    # Attempt 2 -> RETRY
    d2 = rm.handle_failure(act, res_fail, state)
    assert d2 == RecoveryDecision.RETRY

    # Attempt 3 -> retries exhausted, triggers REPLAN
    d3 = rm.handle_failure(act, res_fail, state)
    assert d3 == RecoveryDecision.REPLAN

    # Attempt 4 -> replan exhausted, triggers FAIL
    d4 = rm.handle_failure(act, res_fail, state)
    assert d4 == RecoveryDecision.FAIL


def test_infinite_loop_and_stagnation_prevention():
    """Verify infinite loop detection terminates safely when identical actions fail repeatedly."""
    rm = DefaultRecoveryManager(max_step_retries=2, max_replans=10, max_total_cycles=50)
    state = TaskState(goal="Loop prevention")
    # Multiple actions with identical payload fingerprint
    act1 = Action(action_id="act-1", target="coding", parameters={"x": 1})
    res_fail = ActionResult(action_id="act-1", success=False, error="Repeated persistent failure")

    # Trigger failures until stagnation threshold is breached
    decision = RecoveryDecision.RETRY
    for _ in range(6):
        decision = rm.handle_failure(act1, res_fail, state)

    # Must terminate with FAIL due to stagnation detection
    assert decision == RecoveryDecision.FAIL


def test_max_total_cycles_enforcement():
    """Verify task terminates safely if max_total_cycles is exceeded."""
    rm = DefaultRecoveryManager(max_total_cycles=5)
    state = TaskState(goal="Max cycle test", attempt_count=5)
    act = Action(action_id="act-1", target="research", parameters={})
    res_fail = ActionResult(action_id="act-1", success=False, error="Error")

    decision = rm.handle_failure(act, res_fail, state)
    assert decision == RecoveryDecision.FAIL

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
 main
