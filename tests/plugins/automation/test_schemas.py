"""Tests for Automation Plugin schemas, enums, validation, and serialization."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from xeren.plugins.automation.schemas import (
    AutomationInput,
    AutomationOperation,
    AutomationResult,
    RetryPolicy,
    StepRunRecord,
    StepStatus,
    TaskHistoryEntry,
    TaskPlan,
    TaskStatus,
    TaskStep,
)


def test_automation_enums():
    """Verify enum values for operations and status flags."""
    assert AutomationOperation.TASK_CREATE.value == "task_create"
    assert AutomationOperation.TASK_PLAN.value == "task_plan"
    assert AutomationOperation.TASK_EXECUTE.value == "task_execute"
    assert AutomationOperation.TASK_PAUSE.value == "task_pause"
    assert AutomationOperation.TASK_RESUME.value == "task_resume"
    assert AutomationOperation.TASK_CANCEL.value == "task_cancel"
    assert AutomationOperation.TASK_STATUS.value == "task_status"
    assert AutomationOperation.TASK_RETRY.value == "task_retry"
    assert AutomationOperation.TASK_DEPENDENCY_MANAGEMENT.value == "task_dependency_management"
    assert AutomationOperation.TASK_HISTORY.value == "task_history"

    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.PLANNING.value == "planning"
    assert TaskStatus.READY.value == "ready"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.PAUSED.value == "paused"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"

    assert StepStatus.PENDING.value == "pending"
    assert StepStatus.RUNNING.value == "running"
    assert StepStatus.COMPLETED.value == "completed"
    assert StepStatus.FAILED.value == "failed"
    assert StepStatus.SKIPPED.value == "skipped"
    assert StepStatus.CANCELLED.value == "cancelled"


def test_retry_policy_defaults_and_validation():
    """Verify RetryPolicy default configurations and boundary constraints."""
    policy = RetryPolicy()
    assert policy.max_retries == 2
    assert policy.initial_interval_seconds == 1.0
    assert policy.backoff_factor == 2.0
    assert policy.max_interval_seconds == 30.0
    assert policy.retryable_errors == []

    # Test invalid values
    with pytest.raises(ValidationError):
        RetryPolicy(max_retries=-1)

    with pytest.raises(ValidationError):
        RetryPolicy(max_retries=15)  # Limit is 10

    with pytest.raises(ValidationError):
        RetryPolicy(backoff_factor=0.5)


def test_task_step_defaults():
    """Verify TaskStep model defaults, dependencies, and serialization."""
    step = TaskStep(
        id="s1",
        plugin_name="data",
        action="profile",
        input_payload={"format": "csv"},
    )
    assert step.id == "s1"
    assert step.plugin_name == "data"
    assert step.action == "profile"
    assert step.depends_on == []
    assert step.status == StepStatus.PENDING
    assert step.is_optional is False
    assert step.timeout_seconds == 60.0
    assert step.output is None

    step_dict = step.model_dump()
    assert step_dict["id"] == "s1"
    assert step_dict["status"] == "pending"


def test_task_plan_structure():
    """Verify TaskPlan creation, step indexing, and defaults."""
    s1 = TaskStep(id="s1", plugin_name="research", action="deep_search")
    s2 = TaskStep(id="s2", plugin_name="verification", action="fact_check", depends_on=["s1"])

    plan = TaskPlan(
        task_id="task_test_123",
        objective="Analyze market data",
        steps=[s1, s2],
    )
    assert plan.task_id == "task_test_123"
    assert plan.objective == "Analyze market data"
    assert len(plan.steps) == 2
    assert plan.status == TaskStatus.PENDING
    assert plan.timeout_seconds == 300.0


def test_step_run_record_and_history_entry():
    """Verify telemetry and audit history schemas."""
    record = StepRunRecord(
        step_id="step_a",
        attempt=1,
        success=True,
        latency_ms=123.45,
    )
    assert record.step_id == "step_a"
    assert record.attempt == 1
    assert record.success is True
    assert record.latency_ms == 123.45
    assert record.error is None

    entry = TaskHistoryEntry(
        task_id="task_1",
        event_type="step_completed",
        step_id="step_a",
        details={"result": "ok"},
    )
    assert entry.task_id == "task_1"
    assert entry.event_type == "step_completed"
    assert isinstance(entry.timestamp, datetime)
    assert entry.details["result"] == "ok"


def test_automation_input_and_result():
    """Verify AutomationInput and AutomationResult serialization."""
    inp = AutomationInput(
        operation=AutomationOperation.TASK_PLAN,
        objective="Scrape and summarize",
        max_steps=20,
    )
    assert inp.operation == AutomationOperation.TASK_PLAN
    assert inp.max_steps == 20
    assert inp.auto_plan is True

    res = AutomationResult(
        operation=AutomationOperation.TASK_PLAN,
        success=True,
        task_id="t1",
        status=TaskStatus.READY,
    )
    assert res.success is True
    assert res.task_id == "t1"
    assert res.status == TaskStatus.READY
    assert res.step_results == {}
    assert res.completed_steps == []
    assert res.failed_steps == []
    assert res.step_errors == {}
    assert res.retry_attempts == {}
    assert res.step_details == []


def test_automation_result_outcome_properties_and_experience_payload():
    """Verify outcome properties and to_experience_payload formatting on populated plan."""
    s1 = TaskStep(
        id="s1",
        title="Extract data",
        plugin_name="data",
        action="extract",
        status=StepStatus.COMPLETED,
        retry_count=1,
        latency_ms=45.2,
    )
    s2 = TaskStep(
        id="s2",
        title="Process data",
        plugin_name="data",
        action="process",
        status=StepStatus.FAILED,
        error="IndexError: out of range",
        latency_ms=12.1,
    )
    plan = TaskPlan(
        task_id="task_test_99",
        objective="Data processing task",
        steps=[s1, s2],
        status=TaskStatus.FAILED,
    )
    res = AutomationResult(
        operation=AutomationOperation.TASK_EXECUTE,
        success=False,
        task_id="task_test_99",
        status=TaskStatus.FAILED,
        plan=plan,
        step_results={"s1": {"count": 100}},
        error="Task failed with step errors: IndexError: out of range",
        latency_ms=57.3,
    )

    assert res.completed_steps == ["s1"]
    assert res.failed_steps == ["s2"]
    assert res.step_errors == {"s2": "IndexError: out of range"}
    assert res.retry_attempts == {"s1": 1}
    assert len(res.step_details) == 2
    assert res.step_details[0]["plugin_name"] == "data"
    assert res.step_details[1]["status"] == "failed"

    payload = res.to_experience_payload()
    assert payload["task_id"] == "task_test_99"
    assert payload["status"] == "failed"
    assert payload["success"] is False
    assert payload["objective"] == "Data processing task"
    assert payload["completed_steps"] == ["s1"]
    assert payload["failed_steps"] == ["s2"]
    assert payload["errors"] == {"s2": "IndexError: out of range"}
    assert payload["retry_attempts"] == {"s1": 1}
    assert payload["step_results"] == {"s1": {"count": 100}}
    assert payload["latency_ms"] == 57.3

