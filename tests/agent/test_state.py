"""Tests for TaskState, TaskStatus, and Observation models."""

import pytest

from xeren.agent.actions import Action, ActionResult, PermissionLevel
from xeren.agent.state import Observation, TaskState, TaskStatus


def test_task_state_initialization():
    """Verify default TaskState creation and attributes."""
    state = TaskState(goal="Analyze market data")
    assert state.goal == "Analyze market data"
    assert state.status == TaskStatus.PENDING
    assert state.is_terminal is False
    assert state.attempt_count == 0
    assert len(state.completed_steps) == 0
    assert len(state.failed_steps) == 0
    assert len(state.remaining_steps) == 0
    assert len(state.observations) == 0
    assert state.artifacts == {}


def test_task_status_terminal_states():
    """Verify terminal status detection."""
    state = TaskState(goal="Test goal")
    assert state.is_terminal is False

    for terminal_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMED_OUT]:
        state.status = terminal_status
        assert state.is_terminal is True

    for non_terminal in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL, TaskStatus.RECOVERING]:
        state.status = non_terminal
        assert state.is_terminal is False


def test_observation_and_artifact_merging():
    """Verify observation recording and artifact accumulation."""
    state = TaskState(goal="Generate code")
    obs = Observation(
        action_id="act-1",
        success=True,
        summary="File generated",
        artifacts_discovered={"code:main.py": "print('hello')"},
    )
    state.record_observation(obs)

    assert len(state.observations) == 1
    assert state.observations[0].summary == "File generated"
    assert "code:main.py" in state.artifacts
    assert state.artifacts["code:main.py"] == "print('hello')"


def test_record_success_and_failure():
    """Verify step tracking on success and failure."""
    act1 = Action(action_id="act-1", target="coding", parameters={"task": "init"})
    act2 = Action(action_id="act-2", target="research", parameters={"query": "ai"})
    state = TaskState(goal="Full pipeline", remaining_steps=[act1, act2])

    res1 = ActionResult(
        action_id="act-1",
        success=True,
        output="Code created",
        artifacts={"file:main.py": "code"},
    )
    state.record_success(act1, res1)

    assert len(state.completed_steps) == 1
    assert len(state.remaining_steps) == 1
    assert state.remaining_steps[0].action_id == "act-2"
    assert "file:main.py" in state.artifacts

    res2_fail = ActionResult(action_id="act-2", success=False, error="Network error")
    state.record_failure(act2, res2_fail)

    assert len(state.failed_steps) == 1
    assert state.failed_steps[0].error == "Network error"


def test_task_state_serialization():
    """Verify TaskState Pydantic serialization roundtrip."""
    state = TaskState(
        goal="Test serialization",
        status=TaskStatus.RUNNING,
        artifacts={"key": "val"},
        metadata={"user_id": "test_user"},
    )
    json_data = state.model_dump_json()
    loaded = TaskState.model_validate_json(json_data)
    assert loaded.task_id == state.task_id
    assert loaded.goal == state.goal
    assert loaded.status == TaskStatus.RUNNING
    assert loaded.artifacts["key"] == "val"
