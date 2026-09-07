"""Tests for ExperiencePlugin integrating with canonical ExperienceRecord and ExperienceDataset."""

import pytest

from xeren.agent.actions import ActionResult
from xeren.agent.plugins.experience import ExperiencePlugin
from xeren.agent.state import TaskState, TaskStatus
from xeren.data.dataset import ExperienceDataset
from xeren.data.schema import ActionStep, ExperienceRecord, VerificationDetails
from xeren.plugins.manager import PluginManager


def test_experience_plugin_records_successful_task():
    """Verify ExperiencePlugin records successful task trajectory into canonical ExperienceRecord."""
    dataset = ExperienceDataset()
    plugin = ExperiencePlugin(dataset=dataset)

    state = TaskState(
        task_id="task-success-1",
        goal="Compute statistical summary",
        status=TaskStatus.COMPLETED,
        completed_steps=[
            ActionResult(action_id="act-1", success=True, output="Dataset loaded", metadata={"target": "data"}),
            ActionResult(action_id="act-2", success=True, output="Mean: 42.0", metadata={"target": "data"}),
        ],
        artifacts={"summary.json": "data"},
    )
    verif = VerificationDetails(verified=True, verifier="test_verifier", score=1.0)

    record = plugin.record_task_state(state=state, verification=verif)

    assert isinstance(record, ExperienceRecord)
    assert record.sample_id == "task-success-1"
    assert record.success is True
    assert record.task == "Compute statistical summary"
    assert len(record.actions) == 2
    assert record.verification.verified is True
    assert len(dataset) == 1
    assert dataset.get("task-success-1") is not None


def test_experience_plugin_records_failed_task():
    """Verify ExperiencePlugin preserves failure trajectory and reason."""
    dataset = ExperienceDataset()
    plugin = ExperiencePlugin(dataset=dataset)

    state = TaskState(
        task_id="task-failed-1",
        goal="Scrape protected endpoint",
        status=TaskStatus.FAILED,
        failed_steps=[
            ActionResult(action_id="act-1", success=False, error="403 Forbidden", metadata={"target": "browser"})
        ],
        metadata={"recovery_strategy": "replan_alternative"},
    )

    record = plugin.record_task_state(state=state)

    assert record.sample_id == "task-failed-1"
    assert record.success is False
    assert record.failure_reason == "403 Forbidden"
    assert record.recovery_strategy == "replan_alternative"
    assert len(record.actions) == 1
    assert record.actions[0].success is False
    assert len(dataset) == 1


def test_experience_plugin_execution_via_plugin_manager():
    """Verify ExperiencePlugin operates through PluginManager."""
    dataset = ExperienceDataset()
    plugin = ExperiencePlugin(dataset=dataset)
    pm = PluginManager()
    pm.register(plugin)

    verif = VerificationDetails(verified=True, verifier="rule", score=1.0)
    rec = ExperienceRecord(
        sample_id="sample-pm-1",
        task="Test task",
        actions=[ActionStep(step_index=0, plan_step="Step 0", tool_name="coding", result="ok")],
        prediction_confidence=1.0,
        verification=verif,
        success=True,
        final_quality_score=1.0,
    )

    exec_res = pm.execute("experience", {"record": rec})
    assert exec_res.success is True
    assert len(dataset) == 1
