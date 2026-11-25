"""End-to-End Integration Test: Goal → MockPlanner → AgentController → Multiple Plugins → Verification → Experience → Completed TaskState."""

import pytest

from xeren.agent.actions import Action
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.browser.plugin import BrowserPlugin
from xeren.agent.controller import AgentController
from xeren.agent.evaluator import DefaultCompletionEvaluator
from xeren.agent.planner import MockPlanner
from xeren.agent.plugins.experience import ExperiencePlugin
from xeren.agent.plugins.verification import VerificationPlugin
from xeren.agent.state import TaskStatus
from xeren.data.dataset import ExperienceDataset
from xeren.data.schema import ExperienceRecord
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.data.plugin import DataPlugin
from xeren.plugins.manager import PluginManager
from xeren.plugins.research.plugin import ResearchPlugin


def test_complete_end_to_end_autonomous_workflow():
    """Complete E2E workflow across multiple existing plugins, verification gate, and experience persistence."""
    # 1. Initialize existing PluginManager with multiple real existing plugins
    pm = PluginManager()
    pm.register(ResearchPlugin())
    pm.register(DataPlugin())
    pm.register(CodingPlugin())
    pm.register(BrowserPlugin(adapter=MockBrowserAdapter()))

    verif_plugin = VerificationPlugin(verifier_name="e2e_rule_verifier")
    pm.register(verif_plugin)

    exp_dataset = ExperienceDataset()
    exp_plugin = ExperiencePlugin(dataset=exp_dataset)
    pm.register(exp_plugin)

    # 2. Formulate multi-step task plan across multiple plugins
    planner = MockPlanner()
    goal = "Research data normalization, inspect sample dataset, and generate python normalization routine"

    act_research = Action(
        action_id="e2e-step-1",
        target="research",
        parameters={"query": "data normalization algorithms"},
        description="Phase 1: Research normalization techniques",
    )
    act_data = Action(
        action_id="e2e-step-2",
        target="data",
        parameters={
            "operation": "inspect",
            "dataset": {
                "name": "sample_features",
                "columns": ["feature_a", "feature_b"],
                "data": [[10.0, 20.0], [30.0, 40.0]],
            },
        },
        description="Phase 2: Inspect sample dataset",
    )
    act_code = Action(
        action_id="e2e-step-3",
        target="coding",
        parameters={
            "operation": "syntax_check",
            "source_code": "def normalize_min_max(vals):\n    mn, mx = min(vals), max(vals)\n    return [(v - mn) / (mx - mn) for v in vals]\n",
        },
        description="Phase 3: Verify normalization code syntax",
    )

    planner.set_plan_for_goal(goal, [act_research, act_data, act_code])

    # 3. Setup AgentController with injected verification and experience plugins
    controller = AgentController(
        planner=planner,
        plugin_manager=pm,
        verification_plugin=verif_plugin,
        experience_plugin=exp_plugin,
        completion_evaluator=DefaultCompletionEvaluator(enforce_verification=True),
        max_total_cycles=20,
    )

    # 4. Execute the complete autonomous task
    state = controller.run(
        goal=goal,
        initial_artifacts={"code:normalize.py": "def normalize_min_max(vals): pass"},
        metadata={"verification_rules": ["exists:code:normalize.py"]},
    )

    # 5. Assert Task Completion State
    assert state.status == TaskStatus.COMPLETED
    assert state.is_terminal is True
    assert len(state.completed_steps) == 3
    assert len(state.failed_steps) == 0
    assert len(state.remaining_steps) == 0
    assert len(state.observations) == 3

    # Check targets executed in order
    targets = [s.metadata.get("target") for s in state.completed_steps]
    assert targets == ["research", "data", "coding"]

    # 6. Assert Verification Plugin Ran and Passed
    assert "verification" in state.metadata
    assert state.metadata["verification"]["verified"] is True
    assert state.metadata["verification"]["verifier"] == "e2e_rule_verifier"
    assert state.metadata["verification"]["score"] >= 0.8

    # 7. Assert Experience Plugin Captured Canonical Trajectory
    assert len(exp_dataset) == 1
    record = exp_dataset.get(state.task_id)
    assert record is not None
    assert isinstance(record, ExperienceRecord)
    assert record.sample_id == state.task_id
    assert record.task == goal
    assert record.success is True
    assert record.verification.verified is True
    assert len(record.actions) == 3
    assert record.actions[0].tool_name == "research"
    assert record.actions[1].tool_name == "data"
    assert record.actions[2].tool_name == "coding"
    assert record.final_quality_score >= 0.8
