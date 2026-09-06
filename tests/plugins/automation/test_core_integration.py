"""Integration tests for XerenCore with Automation Plugin and full 9-plugin coexistence."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.automation.schemas import (
    AutomationOperation,
    AutomationResult,
    StepStatus,
    TaskStatus,
    TaskStep,
)


def test_core_coexistence_all_nine_plugins():
    """Verify XerenCore boots with all 9 standard plugins cleanly registered and healthy."""
    core = XerenCore()
    plugin_names = [p.name for p in core.list_plugins()]

    expected_plugins = [
        "research",
        "knowledge",
        "coding",
        "website",
        "data",
        "file",
        "verification",
        "experience",
        "automation",
    ]
    for expected in expected_plugins:
        assert expected in plugin_names, f"Missing plugin: {expected}"

    assert len(plugin_names) >= 9
    assert core.has_plugin("automation")

    # Verify overall health
    health_report = core.check_health()
    assert health_report["healthy"] is True
    assert "automation" in health_report["plugins"]
    assert health_report["plugins"]["automation"]["status"] == "healthy"


def test_core_create_and_plan_task():
    """Verify core.create_task and core.plan_task convenience methods."""
    core = XerenCore()

    # Create task
    create_res = core.create_task(
        objective="Analyze quarterly metrics and verify report",
        steps=[
            TaskStep(id="s1", plugin_name="data", action="profile"),
            TaskStep(id="s2", plugin_name="verification", action="verify", depends_on=["s1"]),
        ],
    )
    assert create_res.success is True
    assert isinstance(create_res, AutomationResult)
    assert create_res.task_id is not None
    assert create_res.plan is not None
    assert len(create_res.plan.steps) == 2

    # Plan task
    plan_res = core.plan_task(
        steps=create_res.plan.steps,
    )
    assert plan_res.success is True
    assert plan_res.metadata["topological_order"] == ["s1", "s2"]


def test_core_execute_task_pipeline():
    """Verify core.execute_task coordinates a pipeline across plugins."""
    core = XerenCore()

    auto_p = core.get_plugin("automation")
    assert isinstance(auto_p, AutomationPlugin)

    # Inject mock dispatcher for deterministic cross-plugin pipeline testing
    executed = []

    def mock_dispatcher(plugin: str, payload: dict, timeout=None):
        executed.append(plugin)
        if plugin == "data":
            return {"dataset_shape": [50, 4], "summary": "Metrics dataset"}
        elif plugin == "file":
            return {"file_created": "report.txt", "size": 1024}
        elif plugin == "verification":
            return {"verified": True, "confidence": 0.95}
        return {"status": "ok"}

    auto_p.registry.set_custom_dispatcher(mock_dispatcher)

    # Define 3-step pipeline: data -> file -> verification
    steps = [
        TaskStep(id="step_data", plugin_name="data", action="profile"),
        TaskStep(
            id="step_file",
            plugin_name="file",
            action="write",
            input_payload={"content": "${steps.step_data.output.summary}"},
            depends_on=["step_data"],
        ),
        TaskStep(
            id="step_verify",
            plugin_name="verification",
            action="verify",
            input_payload={"candidate": "${steps.step_file.output.file_created}"},
            depends_on=["step_file"],
        ),
    ]

    create_res = core.create_task(objective="End-to-end data pipeline", steps=steps)
    task_id = create_res.task_id

    exec_res = core.execute_task(task_id=task_id)
    assert exec_res.success is True
    assert exec_res.status == TaskStatus.COMPLETED
    assert executed == ["data", "file", "verification"]

    # Verify outputs passed and recorded
    assert exec_res.step_results["step_data"]["dataset_shape"] == [50, 4]
    assert exec_res.step_results["step_file"]["file_created"] == "report.txt"
    assert exec_res.step_results["step_verify"]["verified"] is True


def test_core_task_lifecycle_controls():
    """Verify pause, resume, cancel, status, and history methods on Core."""
    core = XerenCore()
    auto_p = core.get_plugin("automation")
    assert isinstance(auto_p, AutomationPlugin)
    auto_p.registry.set_custom_dispatcher(lambda p, d, t: {"status": "ok"})

    create_res = core.create_task(
        objective="Lifecycle testing task",
        steps=[TaskStep(id="s1", plugin_name="data", action="inspect")],
    )
    task_id = create_res.task_id
    assert task_id is not None

    # Check status
    status_res = core.get_task_status(task_id)
    assert status_res.success is True
    assert status_res.task_id == task_id

    # Pause
    pause_res = core.pause_task(task_id, reason="Testing pause")
    assert pause_res.success is True
    assert pause_res.status == TaskStatus.PAUSED

    # Resume
    resume_res = core.resume_task(task_id)
    assert resume_res.success is True

    # Cancel a separate pending/active task
    create_res2 = core.create_task(
        objective="Cancel testing task",
        steps=[TaskStep(id="s2", plugin_name="data", action="inspect")],
    )
    task_id2 = create_res2.task_id
    assert task_id2 is not None
    cancel_res = core.cancel_task(task_id2, reason="Testing cancel")
    assert cancel_res.success is True
    assert cancel_res.status == TaskStatus.CANCELLED

    # History
    hist_res = core.get_task_history(task_id)
    assert hist_res.success is True
    assert len(hist_res.history) >= 2


@pytest.mark.asyncio
async def test_core_async_automation_methods():
    """Verify async automation methods on Core: aautomate, aexecute_task."""
    core = XerenCore()
    auto_p = core.get_plugin("automation")
    assert isinstance(auto_p, AutomationPlugin)
    auto_p.registry.set_custom_dispatcher(lambda p, d, t: {"async": True})

    create_res = core.create_task(
        objective="Async core test",
        steps=[TaskStep(id="s1", plugin_name="research", action="search")],
    )
    task_id = create_res.task_id
    assert task_id is not None

    exec_res = await core.aexecute_task(task_id=task_id)
    assert exec_res.success is True
    assert exec_res.status == TaskStatus.COMPLETED
