"""Tests for TaskExecutorTool: execution, failure isolation, cancellation, pause/resume, and timeouts."""

import pytest

from xeren.plugins.automation.schemas import (
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from xeren.plugins.automation.tools.executor import TaskExecutorTool
from xeren.plugins.automation.tools.state import TaskStateManager


def test_executor_linear_pipeline():
    """Verify linear execution of steps with data passing between steps."""
    sm = TaskStateManager()
    sm.clear()

    executed_calls = []

    def mock_dispatcher(plugin: str, payload: dict, timeout=None):
        executed_calls.append((plugin, payload))
        if plugin == "step_plugin_1":
            return {"val": 42}
        elif plugin == "step_plugin_2":
            return {"result": payload.get("input_val", 0) * 2}
        return {"done": True}

    executor = TaskExecutorTool(
        state_manager=sm,
        custom_dispatcher=mock_dispatcher,
    )

    s1 = TaskStep(id="s1", plugin_name="step_plugin_1", action="action1", input_payload={})
    s2 = TaskStep(
        id="s2",
        plugin_name="step_plugin_2",
        action="action2",
        input_payload={"input_val": "${steps.s1.output.val}"},
        depends_on=["s1"],
    )

    plan = TaskPlan(task_id="task_linear", objective="Linear pipeline", steps=[s1, s2])
    sm.save_plan(plan)

    res_plan = executor.execute_task("task_linear")
    assert res_plan.status == TaskStatus.COMPLETED
    assert res_plan.steps[0].status == StepStatus.COMPLETED
    assert res_plan.steps[0].output == {"val": 42}
    assert res_plan.steps[1].status == StepStatus.COMPLETED
    assert res_plan.steps[1].output == {"result": 84}


def test_executor_failure_isolation_optional_step():
    """Verify optional step failure does not fail the overall task."""
    sm = TaskStateManager()
    sm.clear()

    def mock_dispatcher(plugin: str, payload: dict, timeout=None):
        if plugin == "failing_plugin":
            raise RuntimeError("Optional service offline")
        return {"status": "ok"}

    executor = TaskExecutorTool(
        state_manager=sm,
        custom_dispatcher=mock_dispatcher,
    )

    s1 = TaskStep(id="s1", plugin_name="good_plugin", action="act")
    s2 = TaskStep(id="s2", plugin_name="failing_plugin", action="act", is_optional=True)
    s3 = TaskStep(id="s3", plugin_name="good_plugin", action="act", depends_on=["s1"])

    plan = TaskPlan(task_id="task_opt", objective="Optional step test", steps=[s1, s2, s3])
    sm.save_plan(plan)

    res_plan = executor.execute_task("task_opt")
    assert res_plan.status == TaskStatus.COMPLETED
    assert res_plan.steps[0].status == StepStatus.COMPLETED
    assert res_plan.steps[1].status == StepStatus.FAILED
    assert res_plan.steps[2].status == StepStatus.COMPLETED


def test_executor_required_step_failure():
    """Verify failure of a required step halts downstream execution and marks task FAILED."""
    sm = TaskStateManager()
    sm.clear()

    def mock_dispatcher(plugin: str, payload: dict, timeout=None):
        if plugin == "failing_plugin":
            raise RuntimeError("Critical database crash")
        return {"status": "ok"}

    executor = TaskExecutorTool(
        state_manager=sm,
        custom_dispatcher=mock_dispatcher,
    )

    s1 = TaskStep(id="s1", plugin_name="failing_plugin", action="act", is_optional=False)
    s2 = TaskStep(id="s2", plugin_name="good_plugin", action="act", depends_on=["s1"])

    plan = TaskPlan(task_id="task_fail", objective="Required fail test", steps=[s1, s2])
    sm.save_plan(plan)

    res_plan = executor.execute_task("task_fail")
    assert res_plan.status == TaskStatus.FAILED
    assert res_plan.steps[0].status == StepStatus.FAILED
    assert res_plan.steps[1].status == StepStatus.SKIPPED


def test_executor_cancel_stops_execution():
    """Verify cancelled tasks abort execution immediately."""
    sm = TaskStateManager()
    sm.clear()

    call_count = 0

    def mock_dispatcher(plugin: str, payload: dict, timeout=None):
        nonlocal call_count
        call_count += 1
        # Cancel task after first step finishes
        sm.cancel_task("task_cancel_run")
        return {"step": call_count}

    executor = TaskExecutorTool(
        state_manager=sm,
        custom_dispatcher=mock_dispatcher,
    )

    s1 = TaskStep(id="s1", plugin_name="p", action="a")
    s2 = TaskStep(id="s2", plugin_name="p", action="a", depends_on=["s1"])

    plan = TaskPlan(task_id="task_cancel_run", objective="Cancel test", steps=[s1, s2])
    sm.save_plan(plan)

    res_plan = executor.execute_task("task_cancel_run")
    assert res_plan.status == TaskStatus.CANCELLED
    assert call_count == 1
    assert res_plan.steps[1].status == StepStatus.CANCELLED


@pytest.mark.asyncio
async def test_executor_aexecute_task():
    """Verify asynchronous execution runs identically."""
    sm = TaskStateManager()
    sm.clear()

    def mock_dispatcher(plugin: str, payload: dict, timeout=None):
        return {"async_done": True}

    executor = TaskExecutorTool(
        state_manager=sm,
        custom_dispatcher=mock_dispatcher,
    )

    s1 = TaskStep(id="s1", plugin_name="p", action="a")
    plan = TaskPlan(task_id="task_async", objective="Async run test", steps=[s1])
    sm.save_plan(plan)

    res_plan = await executor.aexecute_task("task_async")
    assert res_plan.status == TaskStatus.COMPLETED
    assert res_plan.steps[0].output == {"async_done": True}
