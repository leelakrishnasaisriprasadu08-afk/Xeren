"""Focused tests for Xeren Core <-> Autonomous Agent Integration boundary.

Validates the CorePlannerAdapter, PlanValidator, dependency injection,
chain-of-thought suppression, timeout/failure isolation, permission enforcement,
and AgentController compatibility.
"""

from typing import Any, Dict, Optional
import pytest

from xeren.agent.actions import Action, ActionType, PermissionLevel
from xeren.agent.controller import AgentController
from xeren.agent.interfaces import Planner
from xeren.agent.permissions import DefaultPermissionManager
from xeren.agent.planner import CorePlannerAdapter, MockPlanner, TaskPlan
from xeren.agent.state import TaskState, TaskStatus
from xeren.agent.validator import PlanValidationError, PlanValidator
from xeren.core.runtime import XerenCore
from xeren.models.providers.mock import MockLLM
from xeren.plugins.manager import PluginManager


# -------------------------------------------------------------------------
# Test 1: Valid Core-generated plan
# -------------------------------------------------------------------------
def test_valid_core_generated_plan() -> None:
    """Verify that a valid JSON plan from a Core model provider is parsed and validated."""
    valid_json = """{
        "goal": "Write a python fibonacci function",
        "steps": [
            {
                "target": "coding",
                "action_type": "plugin",
                "parameters": {"operation": "generate", "task": "Write fibonacci in python"},
                "description": "Generate fibonacci implementation",
                "permission_level": "safe"
            }
        ]
    }"""
    mock_llm = MockLLM(canned_response=valid_json)
    adapter = CorePlannerAdapter(model_provider=mock_llm)

    plan = adapter.plan("Write a python fibonacci function")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) == 1
    assert plan.steps[0].target == "coding"
    assert plan.steps[0].parameters["operation"] == "generate"
    assert plan.steps[0].permission_level == PermissionLevel.SAFE


# -------------------------------------------------------------------------
# Test 2: Malformed model output
# -------------------------------------------------------------------------
def test_malformed_model_output_safe_handling() -> None:
    """Verify that malformed JSON or corrupted text from a model is handled safely."""
    broken_output = "I am an AI and here is what I think: {not valid json... broken syntax"
    mock_llm = MockLLM(canned_response=broken_output)

    # With fallback_to_rule_planner=True (default), it safely falls back to rule plan
    adapter = CorePlannerAdapter(model_provider=mock_llm, fallback_to_rule_planner=True)
    plan = adapter.plan("Write a python script")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 1
    assert "provider_failure" in plan.metadata

    # With fallback disabled, it raises PlanValidationError
    strict_adapter = CorePlannerAdapter(model_provider=mock_llm, fallback_to_rule_planner=False)
    with pytest.raises(PlanValidationError):
        strict_adapter.plan("Write a python script")


# -------------------------------------------------------------------------
# Test 3: Invalid action type
# -------------------------------------------------------------------------
def test_invalid_action_type_rejected() -> None:
    """Verify that unsupported action types are rejected and never reach the executor."""
    invalid_action_json = """{
        "goal": "Execute invalid action",
        "steps": [
            {
                "target": "coding",
                "action_type": "unsupported_magic_type",
                "parameters": {"task": "do something"}
            }
        ]
    }"""
    mock_llm = MockLLM(canned_response=invalid_action_json)
    strict_adapter = CorePlannerAdapter(model_provider=mock_llm, fallback_to_rule_planner=False)

    with pytest.raises(PlanValidationError) as excinfo:
        strict_adapter.plan("Execute invalid action")
    assert "invalid action_type" in str(excinfo.value)


# -------------------------------------------------------------------------
# Test 4: Unknown plugin target
# -------------------------------------------------------------------------
def test_unknown_plugin_target_safe_failure() -> None:
    """Verify that an unknown plugin target causes validation failure and never reaches executor."""
    unknown_target_json = """{
        "goal": "Hack mainframe",
        "steps": [
            {
                "target": "nonexistent_alien_plugin",
                "action_type": "plugin",
                "parameters": {"cmd": "launch"}
            }
        ]
    }"""
    mock_llm = MockLLM(canned_response=unknown_target_json)
    pm = PluginManager()  # empty plugin manager
    strict_adapter = CorePlannerAdapter(
        model_provider=mock_llm,
        plugin_manager=pm,
        fallback_to_rule_planner=False,
    )

    with pytest.raises(PlanValidationError) as excinfo:
        strict_adapter.plan("Hack mainframe")
    assert "unknown plugin/tool" in str(excinfo.value)


# -------------------------------------------------------------------------
# Test 5: Invalid parameters
# -------------------------------------------------------------------------
def test_invalid_parameters_rejected() -> None:
    """Verify that non-dictionary action parameters are rejected by the validator."""
    bad_params_json = """{
        "goal": "Test bad params",
        "steps": [
            {
                "target": "coding",
                "action_type": "plugin",
                "parameters": "not_a_dictionary_string"
            }
        ]
    }"""
    mock_llm = MockLLM(canned_response=bad_params_json)
    strict_adapter = CorePlannerAdapter(model_provider=mock_llm, fallback_to_rule_planner=False)

    with pytest.raises(PlanValidationError) as excinfo:
        strict_adapter.plan("Test bad params")
    assert "parameters" in str(excinfo.value)


# -------------------------------------------------------------------------
# Test 6: Permission-required action detection
# -------------------------------------------------------------------------
def test_permission_required_action_upgraded() -> None:
    """Verify that destructive actions (e.g. delete file) are upgraded to REQUIRES_APPROVAL."""
    delete_json = """{
        "goal": "Delete production database",
        "steps": [
            {
                "target": "file",
                "action_type": "plugin",
                "parameters": {"operation": "delete", "file_path": "/data/prod.db"},
                "description": "Delete production database",
                "permission_level": "safe"
            }
        ]
    }"""
    mock_llm = MockLLM(canned_response=delete_json)
    adapter = CorePlannerAdapter(model_provider=mock_llm)

    plan = adapter.plan("Delete production database")
    assert len(plan.steps) == 1
    # Must be upgraded from safe to requires_approval!
    assert plan.steps[0].permission_level == PermissionLevel.REQUIRES_APPROVAL


# -------------------------------------------------------------------------
# Test 7: Model timeout handling
# -------------------------------------------------------------------------
def test_model_timeout_handled_safely() -> None:
    """Verify that a slow or hanging model provider times out safely without crashing."""
    import time

    def slow_planner(goal: str, context: Optional[Dict[str, Any]]) -> str:
        time.sleep(0.3)
        return "{}"

    adapter = CorePlannerAdapter(
        model_provider=slow_planner,
        timeout_seconds=0.05,
        fallback_to_rule_planner=True,
    )

    plan = adapter.plan("Write python code")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 1
    assert "provider_failure" in plan.metadata
    assert "timed out" in plan.metadata["provider_failure"]


# -------------------------------------------------------------------------
# Test 8: Model failure handling
# -------------------------------------------------------------------------
def test_model_failure_handled_safely() -> None:
    """Verify that provider network/runtime exceptions are caught and isolated."""
    failing_llm = MockLLM(error_to_raise=ConnectionResetError("Remote server disconnected"))
    adapter = CorePlannerAdapter(
        model_provider=failing_llm,
        fallback_to_rule_planner=True,
    )

    plan = adapter.plan("Analyze dataset")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 1
    assert "provider_failure" in plan.metadata
    assert "Remote server disconnected" in plan.metadata["provider_failure"]


# -------------------------------------------------------------------------
# Test 9: Deterministic / mock planner compatibility
# -------------------------------------------------------------------------
def test_deterministic_mock_planner_compatibility() -> None:
    """Verify MockPlanner satisfies the Planner contract and can be used interchangeably."""
    mock_planner = MockPlanner()
    assert isinstance(mock_planner, Planner)

    plan = mock_planner.plan("Research generative agents")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 1
    assert plan.steps[0].target == "research"

    state = TaskState(goal="Research generative agents")
    replan = mock_planner.replan(state, "Search query yielded 0 results")
    assert isinstance(replan, TaskPlan)
    assert len(replan.steps) >= 1


# -------------------------------------------------------------------------
# Test 10: Dependency injection
# -------------------------------------------------------------------------
def test_dependency_injection_custom_callable() -> None:
    """Verify CorePlannerAdapter accepts a custom callable model provider."""
    def custom_core_planner(goal: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "goal": goal,
            "steps": [
                {
                    "target": "research",
                    "parameters": {"query": f"Injected: {goal}"},
                    "description": "Custom injected plan step",
                }
            ],
        }

    adapter = CorePlannerAdapter(model_provider=custom_core_planner)
    plan = adapter.plan("Quantum computing")

    assert len(plan.steps) == 1
    assert plan.steps[0].target == "research"
    assert plan.steps[0].parameters["query"] == "Injected: Quantum computing"


def test_dependency_injection_xeren_core() -> None:
    """Verify CorePlannerAdapter accepts a full XerenCore instance."""
    core = XerenCore()
    adapter = CorePlannerAdapter(core=core)
    assert adapter.core is core
    assert adapter.plugin_manager is core.plugin_manager

    plan = adapter.plan("Write python script for log parsing")
    assert isinstance(plan, TaskPlan)
    assert any(s.target == "coding" for s in plan.steps)


# -------------------------------------------------------------------------
# Test 11: Plan validation step limits
# -------------------------------------------------------------------------
def test_plan_validation_step_limits() -> None:
    """Verify validator rejects plans with zero steps or exceeding max_steps."""
    validator = PlanValidator(max_steps=3)

    # Zero steps
    empty_plan = TaskPlan(goal="Empty goal", steps=[])
    res_empty = validator.validate_plan(empty_plan)
    assert res_empty.is_valid is False
    assert any("zero executable steps" in e for e in res_empty.errors)

    # Exceeding step limit
    many_steps = [
        Action(target="research", parameters={"query": str(i)})
        for i in range(5)
    ]
    too_long_plan = TaskPlan(goal="Too long", steps=many_steps)
    res_long = validator.validate_plan(too_long_plan)
    assert res_long.is_valid is False
    assert any("exceeds maximum step limit" in e for e in res_long.errors)


# -------------------------------------------------------------------------
# Test 12: Zero chain-of-thought exposure
# -------------------------------------------------------------------------
def test_zero_chain_of_thought_stored_or_exposed() -> None:
    """Verify that hidden reasoning or <thought> tags are sanitized and never stored in plan."""
    cot_json = """{
        "goal": "Explain neural networks",
        "steps": [
            {
                "target": "research",
                "action_type": "plugin",
                "parameters": {"query": "neural networks"},
                "description": "<thought>The user wants to know about neural networks. Let me search.</thought>Search for neural network fundamentals",
                "metadata": {"thought": "Internal scratchpad", "public_info": "safe"}
            }
        ],
        "metadata": {"chain_of_thought": "hidden thoughts here"}
    }"""
    mock_llm = MockLLM(canned_response=cot_json)
    adapter = CorePlannerAdapter(model_provider=mock_llm)

    plan = adapter.plan("Explain neural networks")
    assert len(plan.steps) == 1
    step = plan.steps[0]

    assert "<thought>" not in (step.description or "")
    assert "</thought>" not in (step.description or "")
    assert "Internal scratchpad" not in str(step.metadata)
    assert "hidden thoughts" not in str(plan.metadata)
    assert "thought" not in step.metadata
    assert "chain_of_thought" not in plan.metadata


# -------------------------------------------------------------------------
# Test 13: AgentController compatibility
# -------------------------------------------------------------------------
def test_agent_controller_compatibility_with_core_planner_adapter() -> None:
    """Verify AgentController seamlessly executes with CorePlannerAdapter."""
    plan_json = """{
        "goal": "Write a python module",
        "steps": [
            {
                "target": "coding",
                "action_type": "plugin",
                "parameters": {"operation": "generate", "task": "create math module"},
                "description": "Generate math module"
            }
        ]
    }"""
    mock_llm = MockLLM(canned_response=plan_json)
    core = XerenCore()
    adapter = CorePlannerAdapter(core=core, model_provider=mock_llm)

    controller = AgentController(
        planner=adapter,
        plugin_manager=core.plugin_manager,
    )

    state = controller.run("Write a python module")
    assert state.status == TaskStatus.COMPLETED
    assert state.attempt_count >= 1
    assert len(state.completed_steps) >= 1
    assert len(state.observations) >= 1
    assert state.completed_steps[0].action_id is not None
