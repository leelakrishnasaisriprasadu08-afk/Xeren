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
