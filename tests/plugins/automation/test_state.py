"""Tests for TaskStateManager: plan persistence, step updates, lifecycle flags, and audit records."""

from xeren.plugins.automation.schemas import (
    StepRunRecord,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from xeren.plugins.automation.tools.state import TaskStateManager


def test_state_manager_save_and_retrieve_plan():
    """Verify storing, retrieving, and listing task plans."""
    sm = TaskStateManager()
    sm.clear()

    step = TaskStep(id="s1", plugin_name="data", action="clean")
    plan = TaskPlan(task_id="task_100", objective="Data pipeline", steps=[step])

    sm.save_plan(plan)
    retrieved = sm.get_plan("task_100")
    assert retrieved is not None
    assert retrieved.task_id == "task_100"
    assert retrieved.objective == "Data pipeline"

    all_plans = sm.list_tasks()
    assert len(all_plans) == 1
    assert all_plans[0].task_id == "task_100"

    assert sm.get_plan("non_existent") is None


def test_state_manager_status_transitions():
    """Verify updating task status logs transition history."""
    sm = TaskStateManager()
    sm.clear()

    plan = TaskPlan(task_id="task_200", objective="Run checks", steps=[])
    sm.save_plan(plan)

    updated = sm.update_task_status("task_200", TaskStatus.RUNNING)
    assert updated is True
    plan_200 = sm.get_plan("task_200")
    assert plan_200 is not None
    assert plan_200.status == TaskStatus.RUNNING

    history = sm.get_history("task_200")
    assert any(h.event_type == "status_transition" and h.details["to"] == "running" for h in history)


def test_state_manager_step_updates():
    """Verify updating individual step fields like status and output."""
    sm = TaskStateManager()
    sm.clear()

    step = TaskStep(id="s1", plugin_name="coding", action="write")
    plan = TaskPlan(task_id="task_300", objective="Code gen", steps=[step])
    sm.save_plan(plan)

    updated = sm.update_step("task_300", "s1", {"status": StepStatus.COMPLETED, "output": {"code": "print(1)"}})
    assert updated is True

    plan_now = sm.get_plan("task_300")
    assert plan_now is not None
    assert plan_now.steps[0].status == StepStatus.COMPLETED
    assert plan_now.steps[0].output == {"code": "print(1)"}

    # Updating unknown step returns False
    assert sm.update_step("task_300", "unknown_step", {}) is False


def test_state_manager_pause_and_resume():
    """Verify pausing and resuming lifecycle transitions."""
    sm = TaskStateManager()
    sm.clear()

    plan = TaskPlan(task_id="task_pause_test", objective="Test pause", steps=[])
    sm.save_plan(plan)

    # Initial state
    assert sm.is_paused("task_pause_test") is False

    # Pause
    paused = sm.pause_task("task_pause_test")
    assert paused is True
    assert sm.is_paused("task_pause_test") is True
    plan_pause = sm.get_plan("task_pause_test")
    assert plan_pause is not None
    assert plan_pause.status == TaskStatus.PAUSED

    # Resume
    resumed = sm.resume_task("task_pause_test")
    assert resumed is True
    assert sm.is_paused("task_pause_test") is False
    plan_resumed = sm.get_plan("task_pause_test")
    assert plan_resumed is not None
    assert plan_resumed.status == TaskStatus.RUNNING


def test_state_manager_cancel_task():
    """Verify cancelling task sets flag and marks unfinished steps CANCELLED."""
    sm = TaskStateManager()
    sm.clear()

    s1 = TaskStep(id="s1", plugin_name="p", action="a", status=StepStatus.COMPLETED)
    s2 = TaskStep(id="s2", plugin_name="p", action="a", status=StepStatus.RUNNING)
    s3 = TaskStep(id="s3", plugin_name="p", action="a", status=StepStatus.PENDING)

    plan = TaskPlan(task_id="task_cancel_test", objective="Test cancel", steps=[s1, s2, s3])
    sm.save_plan(plan)

    cancelled = sm.cancel_task("task_cancel_test")
    assert cancelled is True
    assert sm.is_cancelled("task_cancel_test") is True

    updated_plan = sm.get_plan("task_cancel_test")
    assert updated_plan is not None
    assert updated_plan.status == TaskStatus.CANCELLED
    assert updated_plan.steps[0].status == StepStatus.COMPLETED
    assert updated_plan.steps[1].status == StepStatus.CANCELLED
    assert updated_plan.steps[2].status == StepStatus.CANCELLED


def test_state_manager_run_records_and_history():
    """Verify recording telemetry run records and querying across tasks."""
    sm = TaskStateManager()
    sm.clear()

    rec1 = StepRunRecord(step_id="step_x", attempt=1, success=False, error="timeout", latency_ms=100.0)
    rec2 = StepRunRecord(step_id="step_x", attempt=2, success=True, latency_ms=50.0)
    sm.add_run_record("task_telemetry", rec1)
    sm.add_run_record("task_telemetry", rec2)

    records = sm.get_run_records("task_telemetry")
    assert len(records) == 2
    step_records = sm.get_run_records("task_telemetry", step_id="step_x")
    assert len(step_records) == 2

    # Global history retrieval
    sm.add_history("task_1", "event_1")
    sm.add_history("task_2", "event_2")
    global_hist = sm.get_history()
    assert len(global_hist) >= 2
