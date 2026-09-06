import pytest

from xeren.agent.evaluator import Evaluator
from xeren.agent.types import AgentAction, ActionResult, AgentState


def test_evaluator_step_budget_overflow():
    evaluator = Evaluator(max_steps=5)
    state = AgentState(
        session_id="s1",
        task="Test budget overflow",
        plan=["step 1", "step 2"],
        step_count=5,
    )
    result = evaluator.evaluate(state)
    assert result.is_complete is True
    assert result.success is False
    assert result.score == 0.0
    assert "Exceeded maximum allowable steps" in result.reason


def test_evaluator_plan_completion_success():
    evaluator = Evaluator(max_steps=10)
    action1 = AgentAction(action_id="1", action_type="navigate", target="https://example.com")
    res1 = ActionResult(action_id="1", success=True)
    action2 = AgentAction(action_id="2", action_type="extract")
    res2 = ActionResult(action_id="2", success=True)

    state = AgentState(
        session_id="s2",
        task="Complete plan",
        plan=["Navigate to https://example.com", "Extract data"],
        step_count=2,
        history=[(action1, res1), (action2, res2)],
    )
    result = evaluator.evaluate(state)
    assert result.is_complete is True
    assert result.success is True
    assert result.score == 1.0
    assert "All planned execution steps completed" in result.reason


def test_evaluator_plan_completion_with_failures():
    evaluator = Evaluator(max_steps=10)
    action1 = AgentAction(action_id="1", action_type="navigate", target="https://example.com")
    res1 = ActionResult(action_id="1", success=True)
    action2 = AgentAction(action_id="2", action_type="extract")
    res2 = ActionResult(action_id="2", success=False, error="Extraction failed")

    state = AgentState(
        session_id="s3",
        task="Complete plan with failure",
        plan=["Navigate", "Extract"],
        step_count=2,
        history=[(action1, res1), (action2, res2)],
    )
    result = evaluator.evaluate(state)
    assert result.is_complete is True
    assert result.success is False
    assert result.score == 0.5
    assert "Plan finished with failures" in result.reason


def test_evaluator_unrecoverable_error():
    evaluator = Evaluator(max_steps=10)
    action = AgentAction(action_id="1", action_type="upload", consequential=True)
    res = ActionResult(
        action_id="1",
        success=False,
        error="Permission denied",
        error_code="PERMISSION_DENIED",
        recoverable=False,
    )

    state = AgentState(
        session_id="s4",
        task="Unrecoverable action",
        plan=["Upload file"],
        step_count=0,
        history=[(action, res)],
    )
    result = evaluator.evaluate(state)
    assert result.is_complete is True
    assert result.success is False
    assert result.score == 0.0
    assert "Unrecoverable error" in result.reason


def test_evaluator_in_progress():
    evaluator = Evaluator(max_steps=10)
    state = AgentState(
        session_id="s5",
        task="Ongoing task",
        plan=["Step 1", "Step 2", "Step 3"],
        step_count=1,
        current_step="Step 2",
    )
    result = evaluator.evaluate(state)
    assert result.is_complete is False
    assert result.success is False
    assert "in progress" in result.reason
