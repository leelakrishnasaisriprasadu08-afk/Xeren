"""Comprehensive integration tests for the Xeren Core Integration Boundary.

Covers the complete Target Flow:
User Goal -> Xeren Core -> CorePlannerAdapter -> TaskPlan -> AgentController ->
PluginManager -> Required Plugin(s) -> Verification -> Experience -> Result.

Includes tests for:
1. Valid plan generation and validation
2. Malformed plan schema rejection
3. Unknown plugin rejection (UnsupportedPluginError)
4. Missing capability rejection (UnsupportedCapabilityError)
5. Missing/invalid parameters rejection (MissingArgumentError)
6. Permission denial handling
7. Consequential action requiring approval
8. Planner timeout with bounded retry
9. Planner failure and safe error handling
10. Successful full plan execution through XerenCore
11. Verification failure handling
12. Experience recording after success and failure
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.controller import AgentController
from xeren.agent.permissions import PermissionManager, PermissionMode
from xeren.agent.types import ActionCategory, AgentAction, AgentState, AgentStatus
from xeren.core.planner import (
    BaseCoreModelAdapter,
    CorePlannerAdapter,
    DeterministicCoreModelAdapter,
    LLMCoreModelAdapter,
    MissingArgumentError,
    ModelInferenceError,
    PlanContext,
    PlanStep,
    PlanValidationError,
    PlanValidator,
    PlannerTimeoutError,
    TaskPlan,
    UnsafePlanError,
    UnsupportedCapabilityError,
    UnsupportedPluginError,
)
from xeren.core.runtime import XerenCore
from xeren.data.schema import ExperienceRecord, VerificationDetails
from xeren.models.providers.mock import MockLLM
from xeren.plugins.contract import PluginCapability
from xeren.plugins.manager import PluginManager
from xeren.plugins.research.plugin import ResearchPlugin


# =============================================================================
# 1. Valid Plan Generation and Pre-Execution Validation
# =============================================================================

def test_core_planner_valid_plan():
    """1. Verify valid TaskPlan generation and validation through CorePlannerAdapter."""
    core = XerenCore(auto_register_defaults=True)
    planner = CorePlannerAdapter(plugin_manager=core.plugin_manager)

    plan = planner.create_task_plan(
        goal="Research artificial intelligence trends",
        context={"query": "AI agent architectures"},
    )

    assert isinstance(plan, TaskPlan)
    assert plan.goal == "Research artificial intelligence trends"
    assert len(plan.steps) >= 2
    assert plan.steps[0].action_type in {"research", "navigate"}
    assert plan.steps[0].description != ""

    # Validator explicitly passes
    validator = PlanValidator(plugin_manager=core.plugin_manager)
    validator.validate(plan)


# =============================================================================
# 2. Malformed Plan Rejection
# =============================================================================

def test_core_planner_malformed_plan_rejection():
    """2. Verify PlanValidator rejects empty goals, empty steps, or blank descriptions."""
    validator = PlanValidator()

    # Empty goal
    bad_goal_plan = TaskPlan(
        goal="   ",
        steps=[PlanStep(description="Valid step", action_type="navigate", target="https://example.com")],
    )
    with pytest.raises(PlanValidationError, match="non-empty user goal"):
        validator.validate(bad_goal_plan)

    # Empty steps rejected by Pydantic schema
    with pytest.raises(Exception):
        TaskPlan(goal="Some goal", steps=[])

    # Step with blank description
    with pytest.raises(PlanValidationError, match="empty description"):
        bad_desc_plan = TaskPlan(
            goal="Valid goal",
            steps=[PlanStep(description="   ", action_type="navigate", target="https://example.com")],
        )
        validator.validate(bad_desc_plan)

    # Malformed model output with fallback disabled
    mock_llm = MockLLM(canned_response="Not valid JSON at all")
    strict_adapter = LLMCoreModelAdapter(llm=mock_llm, enable_fallback=False)
    with pytest.raises(PlanValidationError, match="Model output failed schema validation"):
        strict_adapter.infer_plan(PlanContext(goal="Test malformed output"))


# =============================================================================
# 3. Unknown Plugin Rejection
# =============================================================================

def test_core_planner_unknown_plugin_rejection():
    """3. Verify PlanValidator rejects plans referencing unregistered plugins."""
    pm = PluginManager()  # Empty manager
    validator = PlanValidator(plugin_manager=pm)

    unsupported_plan = TaskPlan(
        goal="Execute unauthorized plugin",
        steps=[
            PlanStep(
                description="Call crypto miner",
                action_type="plugin",
                plugin_name="unregistered_crypto_miner",
                parameters={"hashrate": 100},
            )
        ],
    )

    with pytest.raises(UnsupportedPluginError) as exc_info:
        validator.validate(unsupported_plan)
    assert "unregistered_crypto_miner" in str(exc_info.value)
    assert exc_info.value.details["plugin_name"] == "unregistered_crypto_miner"


# =============================================================================
# 4. Missing Capability Rejection
# =============================================================================

def test_core_planner_missing_capability_rejection():
    """4. Verify PlanValidator rejects plans requiring undeclared capabilities."""
    pm = PluginManager()
    pm.register(ResearchPlugin())
    validator = PlanValidator(plugin_manager=pm)

    bad_cap_plan = TaskPlan(
        goal="Perform unsupported action on research plugin",
        steps=[
            PlanStep(
                description="Execute code on research plugin",
                action_type="research",
                plugin_name="research",
                capability="non_existent_teleportation_capability",
                parameters={"query": "test"},
            )
        ],
    )

    with pytest.raises(UnsupportedCapabilityError) as exc_info:
        validator.validate(bad_cap_plan)
    assert "non_existent_teleportation_capability" in str(exc_info.value)


# =============================================================================
# 5. Missing / Invalid Parameters Rejection
# =============================================================================

def test_core_planner_missing_parameters_rejection():
    """5. Verify PlanValidator rejects actions missing mandatory parameters before execution."""
    validator = PlanValidator()

    # Navigate missing URL
    nav_plan = TaskPlan(
        goal="Browse missing URL",
        steps=[PlanStep(description="Navigate somewhere", action_type="navigate", parameters={})],
    )
    with pytest.raises(MissingArgumentError, match="missing mandatory 'url' parameter"):
        validator.validate(nav_plan)

    # Type missing text or selector
    type_plan = TaskPlan(
        goal="Type without text",
        steps=[PlanStep(description="Type text", action_type="type", parameters={"selector": "#input"})],
    )
    with pytest.raises(MissingArgumentError, match="missing mandatory 'text' parameter"):
        validator.validate(type_plan)

    # Upload missing file_path
    upload_plan = TaskPlan(
        goal="Upload without path",
        steps=[PlanStep(description="Upload file", action_type="upload", parameters={"selector": "input"})],
    )
    with pytest.raises(MissingArgumentError, match="missing mandatory 'file_path' parameter"):
        validator.validate(upload_plan)


# =============================================================================
# 6. Unsafe Plan Execution Guard
# =============================================================================

def test_core_planner_unsafe_execution_blocked():
    """Verify arbitrary dangerous command patterns are blocked before execution."""
    validator = PlanValidator()
    unsafe_plan = TaskPlan(
        goal="Run malicious shell script",
        steps=[
            PlanStep(
                description="Execute shell command",
                action_type="navigate",
                target="https://example.com",
                parameters={"command": "rm -rf / --no-preserve-root"},
            )
        ],
    )

    with pytest.raises(UnsafePlanError, match="Arbitrary code execution is blocked"):
        validator.validate(unsafe_plan)


# =============================================================================
# 7. Permission Denial Handling
# =============================================================================

@pytest.mark.asyncio
async def test_core_planner_permission_denial():
    """6. Verify consequential action is blocked when PermissionManager denies it."""
    # Explicitly deny consequential actions
    pm = PermissionManager(mode=PermissionMode.STRICT)
    browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=browser, permission_manager=pm)

    consequential_action = AgentAction(
        action_id="act-blocked",
        action_type="upload",
        target="input[type='file']",
        parameters={"file_path": "data.csv"},
        consequential=True,
        category=ActionCategory.CONSEQUENTIAL,
    )

    # Deny in permission manager
    pm.deny_approval(consequential_action.action_id, reason="Consequential action rejected by policy")

    res = await controller.executor.aexecute(consequential_action)
    assert res.success is False
    assert res.error_code == "PERMISSION_DENIED"
    assert res.recoverable is False


# =============================================================================
# 8. Consequential Action Requiring Approval
# =============================================================================

@pytest.mark.asyncio
async def test_core_planner_consequential_action_approval():
    """7. Verify consequential action is intercepted until explicitly approved."""
    pm = PermissionManager(mode=PermissionMode.AUTO_APPROVE, require_consequential_approval=True)
    browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=browser, permission_manager=pm)

    action = AgentAction(
        action_id="act-approval",
        action_type="download",
        target="#download-report",
        parameters={"trigger_selector": "#download-report"},
        consequential=True,
        category=ActionCategory.CONSEQUENTIAL,
    )

    # 1. First execution attempt without approval -> rejected
    first_res = await controller.executor.aexecute(action)
    assert first_res.success is False
    assert first_res.error_code == "PERMISSION_DENIED"
    assert first_res.error is not None and "consequential and requires user approval" in first_res.error

    # 2. User grants approval
    approved = pm.grant_approval("act-approval")
    assert approved is True

    # 3. Subsequent execution succeeds
    await browser.anavigate("https://example.com")
    second_res = await controller.executor.aexecute(action)
    assert second_res.success is True


# =============================================================================
# 9. Planner Timeout with Bounded Retry
# =============================================================================

@pytest.mark.asyncio
async def test_core_planner_timeout_handling():
    """8. Verify model timeout triggers bounded retry and raises PlannerTimeoutError."""
    # Slow model adapter that exceeds timeout
    slow_adapter = MagicMock(spec=BaseCoreModelAdapter)

    async def _slow_inference(ctx):
        await asyncio.sleep(0.5)
        return {}

    slow_adapter.ainfer_plan = AsyncMock(side_effect=_slow_inference)

    planner = CorePlannerAdapter(
        model_adapter=slow_adapter,
        max_retries=1,
        timeout_seconds=0.05,
    )

    with pytest.raises(PlannerTimeoutError) as exc_info:
        await planner.acreate_task_plan(goal="Fast task")

    assert "timed out after 2 attempts" in str(exc_info.value)
    assert slow_adapter.ainfer_plan.call_count == 2


# =============================================================================
# 10. Planner Failure Handling
# =============================================================================

@pytest.mark.asyncio
async def test_core_planner_model_failure_handling():
    """9. Verify model failure cleanly raises ModelInferenceError after bounded retries."""
    faulty_adapter = MagicMock(spec=BaseCoreModelAdapter)
    faulty_adapter.ainfer_plan = AsyncMock(side_effect=RuntimeError("Model service unavailable"))

    planner = CorePlannerAdapter(
        model_adapter=faulty_adapter,
        max_retries=1,
    )

    with pytest.raises(ModelInferenceError) as exc_info:
        await planner.acreate_task_plan(goal="Failing task")

    assert "Planning failed after 2 attempts" in str(exc_info.value)
    assert faulty_adapter.ainfer_plan.call_count == 2


# =============================================================================
# 11. Full Successful Target Flow Execution
# =============================================================================

@pytest.mark.asyncio
async def test_core_planner_successful_execution_target_flow():
    """10. Verify full Target Flow:
    User Goal -> Xeren Core -> CorePlannerAdapter -> TaskPlan -> AgentController ->
    PluginManager -> Required Plugin(s) -> Verification -> Experience -> Result.
    """
    core = XerenCore(auto_register_defaults=True)
    browser = MockBrowserAdapter()

    result = await core.arun_agent(
        goal="Research artificial intelligence architectures",
        context={"expected_conditions": ["not empty"]},
        browser_adapter=browser,
        verify_outcome=True,
        record_experience=True,
        max_steps=5,
    )

    # 1. Structured Result envelope
    assert result["success"] is True
    assert result["goal"] == "Research artificial intelligence architectures"

    # 2. Validated TaskPlan
    plan = result["plan"]
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 2

    # 3. AgentState
    state = result["state"]
    assert isinstance(state, AgentState)
    assert state.status == AgentStatus.COMPLETED
    assert state.step_count >= 1

    # 4. Verification Output
    verification = result["verification"]
    assert verification is not None
    assert verification.verified is True
    assert verification.score == 1.0

    # 5. Experience Output
    experience = result["experience"]
    assert experience is not None
    assert isinstance(experience.record, ExperienceRecord)
    assert experience.record.is_verified is True
    assert len(experience.fingerprint) == 64


# =============================================================================
# 12. Verification Failure Handling
# =============================================================================

@pytest.mark.asyncio
async def test_core_planner_verification_failure():
    """11. Verify verification plugin fails when actual outcome contradicts expected conditions."""
    core = XerenCore(auto_register_defaults=True)

    # Set impossible verification condition
    result = await core.arun_agent(
        goal="Research machine learning",
        context={"expected_conditions": ["contains impossible_condition_xyz_123"]},
        verify_outcome=True,
        record_experience=True,
        max_steps=5,
    )

    assert result["success"] is True  # Agent task completed
    verification = result["verification"]
    assert verification is not None
    assert verification.verified is False
    assert verification.score == 0.0


# =============================================================================
# 13. Experience Recording After Success and Failure
# =============================================================================

@pytest.mark.asyncio
async def test_core_planner_experience_recording_on_failure():
    """12. Verify ExperiencePlugin creates an unverified ExperienceRecord when agent task fails."""
    core = XerenCore(auto_register_defaults=True)
    browser = MockBrowserAdapter()

    # Intentionally trigger agent step failure
    browser.fail_navigation = True

    result = await core.arun_agent(
        goal="Browse failing site",
        browser_adapter=browser,
        verify_outcome=True,
        record_experience=True,
        max_steps=2,
    )

    assert result["success"] is False
    experience = result["experience"]
    assert experience is not None
    assert isinstance(experience.record, ExperienceRecord)
    assert experience.record.is_verified is False
    assert len(experience.fingerprint) == 64


def test_core_planner_sync_run_agent():
    """Verify synchronous run_agent wrapper completes end-to-end."""
    core = XerenCore(auto_register_defaults=True)
    result = core.run_agent(
        goal="Download financial spreadsheet",
        verify_outcome=True,
        record_experience=True,
        max_steps=5,
    )
    assert result["goal"] == "Download financial spreadsheet"
    assert isinstance(result["plan"], TaskPlan)
