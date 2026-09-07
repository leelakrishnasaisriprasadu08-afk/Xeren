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
