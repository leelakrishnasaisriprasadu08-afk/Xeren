"""Tests for AutomationWorkflow: end-to-end execution of all 10 automation operations."""

import pytest

from xeren.plugins.automation.registry import AutomationToolRegistry
from xeren.plugins.automation.schemas import (
    AutomationInput,
    AutomationOperation,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from xeren.plugins.automation.workflow import AutomationWorkflow


@pytest.fixture
def workflow():
    registry = AutomationToolRegistry()

    def mock_dispatcher(plugin: str, payload: dict, timeout=None):
        return {"result": f"processed_{plugin}"}

    registry.set_custom_dispatcher(mock_dispatcher)
    return AutomationWorkflow(registry=registry)


def test_workflow_task_create(workflow):
    """Verify TASK_CREATE operation creates plan and saves to state."""
    inp = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Create automated report",
        steps=[
            TaskStep(id="s1", plugin_name="research", action="search"),
        ],
    )
    res = workflow.run(inp)
    assert res.success is True
    assert res.operation == AutomationOperation.TASK_CREATE
    assert res.task_id is not None
    assert res.plan is not None
    assert len(res.plan.steps) == 1


def test_workflow_task_plan(workflow):
    """Verify TASK_PLAN operation validates dependencies and returns execution waves."""
    s1 = TaskStep(id="s1", plugin_name="research", action="search")
    s2 = TaskStep(id="s2", plugin_name="data", action="profile", depends_on=["s1"])

    inp = AutomationInput(
        operation=AutomationOperation.TASK_PLAN,
        objective="Multi-step test",
        steps=[s1, s2],
    )
    res = workflow.run(inp)
    assert res.success is True
    assert res.operation == AutomationOperation.TASK_PLAN
    assert "execution_waves" in res.metadata
    assert "topological_order" in res.metadata
    assert res.metadata["topological_order"] == ["s1", "s2"]


def test_workflow_task_execute(workflow):
    """Verify TASK_EXECUTE runs DAG steps and updates status."""
    create_inp = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Run workflow test",
        steps=[
            TaskStep(id="s1", plugin_name="research", action="search"),
            TaskStep(id="s2", plugin_name="data", action="process", depends_on=["s1"]),
        ],
    )
    create_res = workflow.run(create_inp)
    task_id = create_res.task_id

    exec_inp = AutomationInput(
        operation=AutomationOperation.TASK_EXECUTE,
        task_id=task_id,
    )
    exec_res = workflow.run(exec_inp)
    assert exec_res.success is True
    assert exec_res.status == TaskStatus.COMPLETED
    assert exec_res.step_results["s1"] == {"result": "processed_research"}
    assert exec_res.step_results["s2"] == {"result": "processed_data"}


def test_workflow_task_pause_and_resume(workflow):
    """Verify TASK_PAUSE and TASK_RESUME operations."""
    create_inp = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Pause resume test",
        steps=[TaskStep(id="s1", plugin_name="p", action="a")],
    )
    create_res = workflow.run(create_inp)
    task_id = create_res.task_id

    # Pause
    pause_inp = AutomationInput(
        operation=AutomationOperation.TASK_PAUSE,
        task_id=task_id,
        metadata={"reason": "Manual operator hold"},
    )
    pause_res = workflow.run(pause_inp)
    assert pause_res.success is True
    assert pause_res.status == TaskStatus.PAUSED

    # Resume
    resume_inp = AutomationInput(
        operation=AutomationOperation.TASK_RESUME,
        task_id=task_id,
    )
    resume_res = workflow.run(resume_inp)
    assert resume_res.success is True
    assert resume_res.status == TaskStatus.COMPLETED


def test_workflow_task_cancel(workflow):
    """Verify TASK_CANCEL operation halts and marks task cancelled."""
    create_inp = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Cancel test",
        steps=[TaskStep(id="s1", plugin_name="p", action="a")],
    )
    create_res = workflow.run(create_inp)
    task_id = create_res.task_id

    cancel_inp = AutomationInput(
        operation=AutomationOperation.TASK_CANCEL,
        task_id=task_id,
        metadata={"reason": "User aborted"},
    )
    cancel_res = workflow.run(cancel_inp)
    assert cancel_res.success is True
    assert cancel_res.status == TaskStatus.CANCELLED


def test_workflow_task_status(workflow):
    """Verify TASK_STATUS retrieves live task status."""
    create_inp = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Status check test",
        steps=[TaskStep(id="s1", plugin_name="p", action="a")],
    )
    create_res = workflow.run(create_inp)
    task_id = create_res.task_id

    status_inp = AutomationInput(
        operation=AutomationOperation.TASK_STATUS,
        task_id=task_id,
    )
    status_res = workflow.run(status_inp)
    assert status_res.success is True
    assert status_res.task_id == task_id
    assert status_res.plan is not None


def test_workflow_task_retry(workflow):
    """Verify TASK_RETRY resets failed steps and re-executes."""
    s1 = TaskStep(id="s1", plugin_name="p", action="a", status=StepStatus.FAILED)
    plan = TaskPlan(task_id="task_retry_test", objective="Retry test", steps=[s1], status=TaskStatus.FAILED)
    workflow.registry.state_manager.save_plan(plan)

    retry_inp = AutomationInput(
        operation=AutomationOperation.TASK_RETRY,
        task_id="task_retry_test",
        step_id="s1",
    )
    retry_res = workflow.run(retry_inp)
    assert retry_res.success is True
    assert retry_res.status == TaskStatus.COMPLETED
    assert retry_res.step_results["s1"] == {"result": "processed_p"}


def test_workflow_dependency_management(workflow):
    """Verify TASK_DEPENDENCY_MANAGEMENT operation analyzes steps."""
    steps = [
        TaskStep(id="b", plugin_name="p", action="a", depends_on=["a"]),
        TaskStep(id="a", plugin_name="p", action="a"),
    ]
    inp = AutomationInput(
        operation=AutomationOperation.TASK_DEPENDENCY_MANAGEMENT,
        steps=steps,
    )
    res = workflow.run(inp)
    assert res.success is True
    assert res.metadata["topological_order"] == ["a", "b"]
    assert res.metadata["is_acyclic"] is True


def test_workflow_task_history(workflow):
    """Verify TASK_HISTORY queries audit records."""
    create_inp = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Audit test",
        steps=[],
    )
    create_res = workflow.run(create_inp)
    task_id = create_res.task_id

    hist_inp = AutomationInput(
        operation=AutomationOperation.TASK_HISTORY,
        task_id=task_id,
    )
    hist_res = workflow.run(hist_inp)
    assert hist_res.success is True
    assert len(hist_res.history) >= 1


@pytest.mark.asyncio
async def test_workflow_arun(workflow):
    """Verify asynchronous arun() execution."""
    inp = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Async workflow test",
    )
    res = await workflow.arun(inp)
    assert res.success is True
    assert res.task_id is not None
