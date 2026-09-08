 feature/core-architecture
"""Tests for MockPlanner and CorePlannerAdapter."""

import pytest

from xeren.agent.actions import Action
from xeren.agent.planner import CorePlannerAdapter, MockPlanner, TaskPlan
from xeren.agent.state import TaskState
from xeren.core.runtime import XerenCore


def test_mock_planner_canned_goal():
    """Verify MockPlanner returns exact canned plan when registered."""
    planner = MockPlanner()
    step1 = Action(target="research", parameters={"query": "quantum computing"})
    step2 = Action(target="coding", parameters={"task": "simulate qubits"})
    planner.set_plan_for_goal("explore quantum", [step1, step2])

    plan = planner.plan("Please explore quantum algorithms")
    assert len(plan.steps) == 2
    assert plan.steps[0].target == "research"
    assert plan.steps[1].target == "coding"
    assert planner.plan_call_count == 1


def test_mock_planner_rule_inference():
    """Verify rule-based plan inference when no canned plan exists."""
    planner = MockPlanner()

    code_plan = planner.plan("Write python code for a parser")
    assert any(s.target == "coding" for s in code_plan.steps)

    research_plan = planner.plan("Research latest AI developments")
    assert any(s.target == "research" for s in research_plan.steps)

    data_plan = planner.plan("Analyze data trends")
    assert any(s.target == "data" for s in data_plan.steps)


def test_mock_planner_replan():
    """Verify MockPlanner replan behavior."""
    planner = MockPlanner()
    replan_step = Action(target="research", parameters={"query": "alternative query"})
    planner.set_replan_steps([replan_step])

    state = TaskState(goal="Initial goal")
    new_plan = planner.replan(state, failure_reason="Original source timed out")

    assert len(new_plan.steps) == 1
    assert new_plan.steps[0].parameters["query"] == "alternative query"
    assert planner.replan_call_count == 1


def test_core_planner_adapter():
    """Verify CorePlannerAdapter adapts XerenCore to Planner interface."""
    core = XerenCore(auto_register_defaults=True)
    adapter = CorePlannerAdapter(core=core)

    plan = adapter.plan("Write a Python sorting algorithm")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 1
    assert plan.steps[0].target == "coding"

    state = TaskState(goal="Write sorting algorithm")
    replan = adapter.replan(state, failure_reason="Syntax check failed")
    assert isinstance(replan, TaskPlan)
    assert len(replan.steps) >= 1

import pytest

from xeren.agent.planner import Planner
from xeren.agent.types import ActionCategory, AgentState


def test_planner_decomposition_browse():
    planner = Planner()
    plan = planner.create_plan("Browse example.com to find pricing", context={"url": "https://example.com/pricing"})
    assert len(plan) == 4
    assert plan[0] == "Navigate to https://example.com/pricing"
    assert "Observe" in plan[1]
    assert "Extract" in plan[2]
    assert "Verify" in plan[3]


def test_planner_decomposition_download():
    planner = Planner()
    plan = planner.create_plan("Download the financial spreadsheet")
    assert len(plan) == 4
    assert "Navigate to download page" in plan[0]
    assert "Download file" in plan[2]


def test_planner_decomposition_upload():
    planner = Planner()
    plan = planner.create_plan("Upload resume document to the careers portal")
    assert len(plan) == 4
    assert "Navigate to upload page" in plan[0]
    assert "Upload file" in plan[2]


def test_planner_decomposition_generic():
    planner = Planner()
    plan = planner.create_plan("Calculate statistical metrics")
    assert len(plan) == 3
    assert "Analyze task: Calculate statistical metrics" in plan[0]


def test_planner_next_action_navigation():
    planner = Planner()
    state = AgentState(
        session_id="s1",
        task="Navigate to dashboard.example.com",
        plan=["Navigate to dashboard.example.com", "Observe content"],
        step_count=0,
    )
    action = planner.next_action(state)
    assert action is not None
    assert action.action_type == "navigate"
    assert action.target == "https://dashboard.example.com"
    assert action.category == ActionCategory.INTERACTIVE


def test_planner_next_action_observe_and_extract():
    planner = Planner()
    state = AgentState(
        session_id="s2",
        task="Observe and extract page",
        plan=["Observe page", "Extract data"],
        step_count=0,
    )
    obs_action = planner.next_action(state)
    assert obs_action is not None
    assert obs_action.action_type == "observe"
    assert obs_action.category == ActionCategory.READ_ONLY

    state.step_count = 1
    extract_action = planner.next_action(state)
    assert extract_action is not None
    assert extract_action.action_type == "extract"
    assert extract_action.category == ActionCategory.READ_ONLY


def test_planner_next_action_upload_and_download():
    planner = Planner()
    state = AgentState(
        session_id="s3",
        task="Handle files",
        plan=["Download report file", "Upload verified file"],
        step_count=0,
        memory={"download_selector": "#export-btn", "upload_file_path": "report.pdf"},
    )
    dl_action = planner.next_action(state)
    assert dl_action is not None
    assert dl_action.action_type == "download"
    assert dl_action.consequential is True
    assert dl_action.category == ActionCategory.CONSEQUENTIAL
    assert dl_action.target == "#export-btn"

    state.step_count = 1
    up_action = planner.next_action(state)
    assert up_action is not None
    assert up_action.action_type == "upload"
    assert up_action.consequential is True
    assert up_action.parameters.get("file_path") == "report.pdf"


def test_planner_next_action_completion():
    planner = Planner()
    state = AgentState(
        session_id="s4",
        task="Short task",
        plan=["Navigate to https://example.com"],
        step_count=1,
    )
    action = planner.next_action(state)
    assert action is None


def test_planner_replan():
    planner = Planner()
    state = AgentState(
        session_id="s5",
        task="Search items",
        plan=["Navigate to https://example.com", "Click search button", "Extract results"],
        step_count=1,
    )
    new_plan = planner.replan(state, failure_reason="Element '#search-btn' not found")
    assert len(new_plan) == 4
    assert new_plan[0] == "Navigate to https://example.com"
    assert "after failure" in new_plan[1]
    assert "Retry action" in new_plan[2]
    assert state.plan == new_plan
 main
