"""Tests for DefaultObserver."""

import pytest

from xeren.agent.actions import Action, ActionResult
from xeren.agent.observer import DefaultObserver
from xeren.agent.state import TaskState


def test_observer_captures_successful_outcome():
    """Verify observer produces detailed observation on success."""
    observer = DefaultObserver()
    action = Action(target="research", parameters={"query": "Xeren framework"}, description="Initial search")
    result = ActionResult(
        action_id=action.action_id,
        success=True,
        output="Summary of Xeren framework",
        latency_ms=45.2,
        artifacts={"summary.txt": "Xeren"},
    )
    state = TaskState(goal="Research Xeren")

    obs = observer.observe(action, result, state)

    assert obs.action_id == action.action_id
    assert obs.success is True
    assert "completed successfully" in obs.summary
    assert "Initial search" in obs.summary
    assert obs.artifacts_discovered == {"summary.txt": "Xeren"}
    assert obs.metadata["latency_ms"] == 45.2


def test_observer_captures_failed_outcome():
    """Verify observer captures failure reason and error details."""
    observer = DefaultObserver()
    action = Action(target="coding", parameters={"operation": "execute"})
    result = ActionResult(
        action_id=action.action_id,
        success=False,
        error="Execution sandbox timeout",
        latency_ms=3000.0,
    )
    state = TaskState(goal="Run code")

    obs = observer.observe(action, result, state)

    assert obs.success is False
    assert "failed: Execution sandbox timeout" in obs.summary
    assert obs.error == "Execution sandbox timeout"
