"""Tests for DefaultCompletionEvaluator."""

import pytest

from xeren.agent.actions import Action, ActionResult
from xeren.agent.evaluator import DefaultCompletionEvaluator
from xeren.agent.state import TaskState
from xeren.data.schema import VerificationDetails


def test_completion_fails_if_remaining_steps_exist():
    """Verify task is marked incomplete if planned steps remain."""
    evaluator = DefaultCompletionEvaluator()
    state = TaskState(
        goal="Two-step goal",
        completed_steps=[ActionResult(action_id="1", success=True)],
        remaining_steps=[Action(action_id="2", target="coding", parameters={})],
    )
    evaluation = evaluator.evaluate(state)

    assert evaluation.is_complete is False
    assert any("remain unexecuted" in m for m in evaluation.missing_requirements)


def test_completion_fails_if_required_artifacts_missing():
    """Verify evaluator blocks completion when required artifacts are not present."""
    evaluator = DefaultCompletionEvaluator(required_artifact_keys=["report.md", "data.csv"])
    state = TaskState(
        goal="Generate reports",
        completed_steps=[ActionResult(action_id="1", success=True)],
        remaining_steps=[],
        artifacts={"report.md": "# Report"},  # data.csv missing!
    )
    evaluation = evaluator.evaluate(state)

    assert evaluation.is_complete is False
    assert any("data.csv" in m for m in evaluation.missing_requirements)


def test_completion_blocked_by_failed_verification():
    """Verify verification gate: a failed verification prevents task completion."""
    evaluator = DefaultCompletionEvaluator()
    state = TaskState(
        goal="Produce verified code",
        completed_steps=[ActionResult(action_id="1", success=True)],
        remaining_steps=[],
    )
    failed_verif = VerificationDetails(
        verified=False,
        verifier="code_verifier",
        score=0.2,
        details={"error": "Syntax check failed"},
    )
    evaluation = evaluator.evaluate(state, verification_result=failed_verif)

    assert evaluation.is_complete is False
    assert any("verification FAILED" in m for m in evaluation.missing_requirements)


def test_completion_succeeds_when_all_criteria_met():
    """Verify task completes when steps, artifacts, and verification all succeed."""
    evaluator = DefaultCompletionEvaluator(required_artifact_keys=["code:main.py"])
    state = TaskState(
        goal="Build feature",
        completed_steps=[ActionResult(action_id="1", success=True)],
        remaining_steps=[],
        artifacts={"code:main.py": "print(1)"},
    )
    passed_verif = VerificationDetails(
        verified=True,
        verifier="unit_tests",
        score=1.0,
        details={"passed": 5},
    )
    evaluation = evaluator.evaluate(state, verification_result=passed_verif)

    assert evaluation.is_complete is True
    assert evaluation.confidence_score == 1.0
    assert len(evaluation.missing_requirements) == 0

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
