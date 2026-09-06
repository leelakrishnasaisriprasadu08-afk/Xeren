"""Tests for TaskPlannerTool: DAG validation, cycle detection, topological sorting, and template decomposition."""

import pytest

from xeren.plugins.automation.schemas import TaskStep
from xeren.plugins.automation.tools.planner import TaskPlannerError, TaskPlannerTool


def test_planner_validate_dag_valid():
    """Verify clean linear and branching DAGs are validated successfully."""
    planner = TaskPlannerTool()
    steps = [
        TaskStep(id="step_1", plugin_name="research", action="search"),
        TaskStep(id="step_2", plugin_name="data", action="profile", depends_on=["step_1"]),
        TaskStep(id="step_3", plugin_name="coding", action="generate_code", depends_on=["step_1"]),
        TaskStep(id="step_4", plugin_name="verification", action="verify", depends_on=["step_2", "step_3"]),
    ]
    is_valid, error = planner.validate_dag(steps)
    assert is_valid is True
    assert error is None


def test_planner_validate_dag_cycle_detection():
    """Verify cycles are detected and rejected using Kahn's algorithm."""
    planner = TaskPlannerTool()
    # 2-step cycle: A -> B -> A
    steps = [
        TaskStep(id="step_a", plugin_name="plugin1", action="act1", depends_on=["step_b"]),
        TaskStep(id="step_b", plugin_name="plugin2", action="act2", depends_on=["step_a"]),
    ]
    is_valid, error = planner.validate_dag(steps)
    assert is_valid is False
    assert error is not None
    assert "cycle" in error.lower()

    # 3-step cycle: A -> B -> C -> A
    steps_3 = [
        TaskStep(id="step_1", plugin_name="p1", action="a", depends_on=["step_3"]),
        TaskStep(id="step_2", plugin_name="p2", action="b", depends_on=["step_1"]),
        TaskStep(id="step_3", plugin_name="p3", action="c", depends_on=["step_2"]),
    ]
    is_valid, error = planner.validate_dag(steps_3)
    assert is_valid is False
    assert error is not None
    assert "cycle" in error.lower()


def test_planner_validate_dag_self_dependency():
    """Verify a step depending on itself is detected and rejected."""
    planner = TaskPlannerTool()
    steps = [
        TaskStep(id="step_1", plugin_name="p1", action="act1", depends_on=["step_1"]),
    ]
    is_valid, error = planner.validate_dag(steps)
    assert is_valid is False
    assert error is not None
    assert "depend on itself" in error.lower()


def test_planner_validate_dag_unknown_dependency():
    """Verify references to non-existent steps are rejected."""
    planner = TaskPlannerTool()
    steps = [
        TaskStep(id="step_1", plugin_name="p1", action="act1", depends_on=["missing_step"]),
    ]
    is_valid, error = planner.validate_dag(steps)
    assert is_valid is False
    assert error is not None
    assert "missing_step" in error


def test_planner_validate_dag_duplicate_ids():
    """Verify duplicate step IDs are detected and rejected."""
    planner = TaskPlannerTool()
    steps = [
        TaskStep(id="step_1", plugin_name="p1", action="act1"),
        TaskStep(id="step_1", plugin_name="p2", action="act2"),
    ]
    is_valid, error = planner.validate_dag(steps)
    assert is_valid is False
    assert error is not None
    assert "Duplicate step ID" in error


def test_planner_topological_sort():
    """Verify steps are topologically sorted according to their dependencies."""
    planner = TaskPlannerTool()
    steps = [
        TaskStep(id="final", plugin_name="verification", action="verify", depends_on=["mid"]),
        TaskStep(id="mid", plugin_name="data", action="process", depends_on=["initial"]),
        TaskStep(id="initial", plugin_name="research", action="search"),
    ]
    sorted_steps = planner.get_topological_order(steps)
    sorted_ids = [s.id for s in sorted_steps]
    assert sorted_ids == ["initial", "mid", "final"]


def test_planner_execution_waves():
    """Verify execution waves group steps that can run in parallel without unsatisfied dependencies."""
    planner = TaskPlannerTool()
    steps = [
        TaskStep(id="r1", plugin_name="research", action="search"),
        TaskStep(id="r2", plugin_name="research", action="search"),
        TaskStep(id="process1", plugin_name="data", action="process", depends_on=["r1"]),
        TaskStep(id="process2", plugin_name="data", action="process", depends_on=["r2"]),
        TaskStep(id="verify", plugin_name="verification", action="verify", depends_on=["process1", "process2"]),
    ]
    waves = planner.get_execution_waves(steps)
    assert len(waves) == 3

    # Wave 1: r1, r2
    wave1_ids = {s.id for s in waves[0]}
    assert wave1_ids == {"r1", "r2"}

    # Wave 2: process1, process2
    wave2_ids = {s.id for s in waves[1]}
    assert wave2_ids == {"process1", "process2"}

    # Wave 3: verify
    wave3_ids = {s.id for s in waves[2]}
    assert wave3_ids == {"verify"}


def test_planner_plan_from_objective_templates():
    """Verify domain-specific objective template decompositions."""
    planner = TaskPlannerTool()

    # Research objective
    plan_research = planner.plan_from_objective("Research competitor AI architectures and verify results")
    assert len(plan_research.steps) >= 2
    assert any(s.plugin_name == "research" for s in plan_research.steps)
    assert any(s.plugin_name == "verification" for s in plan_research.steps)

    # Data analysis objective
    plan_data = planner.plan_from_objective("Profile dataset, clean missing records, and generate visualization")
    assert len(plan_data.steps) >= 3
    assert any(s.plugin_name == "data" for s in plan_data.steps)

    # Coding objective
    plan_coding = planner.plan_from_objective("Write a python script to parse logs and verify code")
    assert len(plan_coding.steps) >= 2
    assert any(s.plugin_name == "coding" for s in plan_coding.steps)

    # Website objective
    plan_site = planner.plan_from_objective("Build a landing page website and verify responsive layout")
    assert len(plan_site.steps) >= 2
    assert any(s.plugin_name == "website" for s in plan_site.steps)

    # General fallback
    plan_gen = planner.plan_from_objective("Perform general multi-step operation")
    assert len(plan_gen.steps) == 2


def test_planner_cycle_raises_in_topological_sort():
    """Verify TaskPlannerError is raised if topological sort is called on a cyclic graph."""
    planner = TaskPlannerTool()
    steps = [
        TaskStep(id="s1", plugin_name="p", action="a", depends_on=["s2"]),
        TaskStep(id="s2", plugin_name="p", action="a", depends_on=["s1"]),
    ]
    with pytest.raises(TaskPlannerError):
        planner.get_topological_order(steps)
