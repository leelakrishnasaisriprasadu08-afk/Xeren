"""Tests for DeterministicScheduler: step readiness logic and dynamic variable interpolation."""

from xeren.plugins.automation.schemas import StepStatus, TaskPlan, TaskStep
from xeren.plugins.automation.tools.scheduler import DeterministicScheduler


def test_scheduler_step_readiness():
    """Verify scheduler identifies which steps are ready based on dependency status."""
    scheduler = DeterministicScheduler()

    s1 = TaskStep(id="s1", plugin_name="p", action="a", status=StepStatus.PENDING)
    s2 = TaskStep(id="s2", plugin_name="p", action="a", status=StepStatus.PENDING, depends_on=["s1"])
    s3 = TaskStep(id="s3", plugin_name="p", action="a", status=StepStatus.PENDING, depends_on=["s2"])

    plan = TaskPlan(objective="Test readiness", steps=[s1, s2, s3])

    # Initially, only s1 is ready
    ready = scheduler.get_ready_steps(plan)
    assert len(ready) == 1
    assert ready[0].id == "s1"

    # When s1 completes, s2 becomes ready
    plan.steps[0].status = StepStatus.COMPLETED
    ready_after_s1 = scheduler.get_ready_steps(plan)
    assert len(ready_after_s1) == 1
    assert ready_after_s1[0].id == "s2"

    # When s2 fails, s3 should NOT become ready
    plan.steps[1].status = StepStatus.FAILED
    ready_after_fail = scheduler.get_ready_steps(plan)
    assert len(ready_after_fail) == 0


def test_scheduler_variable_interpolation_exact_match():
    """Verify exact match syntax replaces token with raw dictionary/object."""
    scheduler = DeterministicScheduler()
    step_outputs = {
        "step_1": {"profile": {"rows": 100, "cols": 5}, "valid": True},
    }

    payload = {
        "dataset_info": "${steps.step_1.output}",
        "action": "visualize",
    }

    resolved = scheduler.resolve_step_inputs(payload, step_outputs)
    assert resolved["dataset_info"] == {"profile": {"rows": 100, "cols": 5}, "valid": True}
    assert resolved["action"] == "visualize"


def test_scheduler_variable_interpolation_substring():
    """Verify substring token syntax formats nested strings."""
    scheduler = DeterministicScheduler()
    step_outputs = {
        "scrape": {"summary": "Competitor X released product Y", "score": 95},
    }

    payload = {
        "prompt": "Analyze the following finding: ${steps.scrape.output.summary}. Score is ${steps.scrape.output.score}."
    }

    resolved = scheduler.resolve_step_inputs(payload, step_outputs)
    assert resolved["prompt"] == "Analyze the following finding: Competitor X released product Y. Score is 95."


def test_scheduler_variable_interpolation_missing_variable():
    """Verify missing tokens or missing steps leave token or resolve gracefully without crash."""
    scheduler = DeterministicScheduler()
    step_outputs = {
        "step_a": {"result": "ok"},
    }

    payload = {
        "missing_step": "${steps.non_existent.output}",
        "missing_key": "${steps.step_a.output.unknown_key}",
    }

    resolved = scheduler.resolve_step_inputs(payload, step_outputs)
    # Missing step leaves unreplaced or empty
    assert "${steps.non_existent.output}" in str(resolved["missing_step"]) or resolved["missing_step"] == ""


def test_scheduler_list_interpolation():
    """Verify interpolation within lists."""
    scheduler = DeterministicScheduler()
    step_outputs = {
        "s1": {"id": "doc_123"},
    }

    payload = {
        "docs": ["${steps.s1.output.id}", "doc_456"],
    }

    resolved = scheduler.resolve_step_inputs(payload, step_outputs)
    assert resolved["docs"] == ["doc_123", "doc_456"]
