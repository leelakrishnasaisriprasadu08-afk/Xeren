"""Final Xeren 1.0 Comprehensive End-to-End Integration Test Suite.

Validates the complete pipeline:
User Request -> Xeren Core -> Reasoning/Planning -> Autonomous Agent ->
Plugin Manager -> Capabilities (Research, Knowledge/RAG, Coding, Website, Data, Browser) ->
Verification -> Experience -> Final Response.

Covers all 13 required scenarios:
1. Simple knowledge question
2. Research task
3. RAG/document task
4. Coding task
5. Website-generation task
6. Data-analysis task
7. Multi-plugin task
8. Autonomous browser task
9. Failed tool execution
10. Failed verification
11. Permission-required action
12. Invalid user request
13. Agent recovery/replanning
"""

import pytest
import asyncio
from typing import Any, Dict, List

from xeren.core.runtime import XerenCore
from xeren.core.planner import (
    CorePlannerAdapter,
    TaskPlan,
    PlanStep,
    PlanValidator,
    UnsafePlanError,
    PlanValidationError,
)
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.controller import AgentController
from xeren.agent.permissions import PermissionManager, PermissionMode
from xeren.agent.types import AgentAction, ActionCategory, AgentStatus
from xeren.plugins.contract import PluginCapability
from xeren.plugins.coding.schemas import CodingResult
from xeren.plugins.research.schemas import ResearchResult
from xeren.plugins.website.schemas import WebsiteResult
from xeren.plugins.data.schemas import DataResult
from xeren.plugins.knowledge.schemas import KnowledgeResult


# =============================================================================
# Scenario 1: Simple Knowledge Question
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_1_simple_knowledge_question():
    """1. Validate simple knowledge question through Xeren Core pipeline."""
    core = XerenCore(auto_register_defaults=True)

    result = await core.aprocess_request(
        request="Explain the fundamental principles of quantum entanglement question",
        context={"depth": "brief"},
        verify_outcome=True,
        record_experience=True,
    )

    assert result["success"] is True
    assert isinstance(result["plan"], TaskPlan)
    assert len(result["plan"].steps) >= 1
    assert result["final_response"] != ""
    assert result["verification"] is not None
    assert result["experience"] is not None


# =============================================================================
# Scenario 2: Research Task
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_2_research_task():
    """2. Validate autonomous deep research workflow with web search and synthesis."""
    core = XerenCore(auto_register_defaults=True)

    result = await core.aprocess_request(
        request="Research latest advancements in multimodal transformer models",
        context={"depth": "standard"},
        verify_outcome=True,
        record_experience=True,
    )

    assert result["success"] is True
    plan = result["plan"]
    assert any(step.plugin_name == "research" for step in plan.steps)
    assert result["final_response"] != ""
    assert result["verification"].verified is True
    assert result["experience"] is not None
    assert result["experience"].record.verification.verified is True


# =============================================================================
# Scenario 3: RAG / Document Task
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_3_rag_document_task():
    """3. Validate RAG document ingestion, hybrid retrieval, and grounded query resolution."""
    core = XerenCore(auto_register_defaults=True)

    # 1. Ingest proprietary documentation
    ingest_res = await core.aingest_knowledge(
        texts=[
            "Xeren 1.0 is an enterprise autonomous work agent featuring verifiable execution and sovereign deployment.",
            "Xeren utilizes a dual-engine architecture combining modular plugins with Playwright browser automation.",
        ],
        source="enterprise_manual",
    )
    assert ingest_res.operation.value == "ingest"
    assert len(ingest_res.inserted_chunk_ids) >= 2

    # 2. Query through high-level Knowledge / RAG interface
    query_res = await core.aknowledge(
        query="What is the architecture of Xeren 1.0?",
        top_k=2,
        include_provenance=True,
    )
    assert isinstance(query_res, KnowledgeResult)
    assert len(query_res.retrieved_chunks) > 0
    assert any("dual-engine architecture" in c.content for c in query_res.retrieved_chunks)

    # 3. Process natural language query through the unified pipeline
    req_res = await core.aprocess_request(
        request="Retrieve knowledge context for Xeren enterprise manual",
        context={"query": "Xeren 1.0 architecture"},
        verify_outcome=True,
    )
    assert req_res["success"] is True
    assert req_res["final_response"] != ""


# =============================================================================
# Scenario 4: Coding Task
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_4_coding_task():
    """4. Validate autonomous code generation, syntax validation, and sandbox execution."""
    core = XerenCore(auto_register_defaults=True)

    result = await core.aprocess_request(
        request="Generate Python script to compute moving averages of a time series",
        verify_outcome=True,
        record_experience=True,
    )

    assert result["success"] is True
    plan = result["plan"]
    assert any(step.plugin_name == "coding" for step in plan.steps)
    assert result["final_response"] != ""
    assert result["verification"].verified is True


# =============================================================================
# Scenario 5: Website Generation Task
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_5_website_generation_task():
    """5. Validate website generation with HTML/CSS/JS artifacts, security check, and validation."""
    core = XerenCore(auto_register_defaults=True)

    result = await core.aprocess_request(
        request="Generate website landing page for TechSummit 2026 conference",
        verify_outcome=True,
        record_experience=True,
    )

    assert result["success"] is True
    plan = result["plan"]
    assert any(step.plugin_name == "website" for step in plan.steps)
    assert result["final_response"] != ""
    assert result["verification"].verified is True


# =============================================================================
# Scenario 6: Data Analysis Task
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_6_data_analysis_task():
    """6. Validate structured data ingestion, inspection, statistics, and visualization spec."""
    core = XerenCore(auto_register_defaults=True)

    dataset_records = [
        {"timestamp": "2026-01-01", "latency_ms": 120, "error_rate": 0.01},
        {"timestamp": "2026-01-02", "latency_ms": 115, "error_rate": 0.00},
        {"timestamp": "2026-01-03", "latency_ms": 130, "error_rate": 0.02},
    ]

    result = await core.aprocess_request(
        request="Inspect dataset performance metrics for anomalous trends",
        context={"records": dataset_records},
        verify_outcome=True,
        record_experience=True,
    )

    assert result["success"] is True
    plan = result["plan"]
    assert any(step.plugin_name == "data" for step in plan.steps)
    assert result["final_response"] != ""


# =============================================================================
# Scenario 7: Multi-Plugin Task
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_7_multi_plugin_task():
    """7. Validate multi-plugin chained workflow (Research background -> Generate code)."""
    core = XerenCore(auto_register_defaults=True)

    result = await core.aprocess_request(
        request="Multi task: Research distributed consensus algorithms and generate Python implementation",
        verify_outcome=True,
        record_experience=True,
    )

    assert result["success"] is True
    plan = result["plan"]
    plugin_names = {s.plugin_name for s in plan.steps if s.plugin_name}
    assert "research" in plugin_names
    assert "coding" in plugin_names
    assert result["final_response"] != ""
    assert result["experience"] is not None
    assert result["experience"].record.verification.verified is True


# =============================================================================
# Scenario 8: Autonomous Browser Task
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_8_autonomous_browser_task():
    """8. Validate autonomous browser interaction (navigate, observe, extract, cleanup)."""
    core = XerenCore(auto_register_defaults=True)
    mock_browser = MockBrowserAdapter()

    result = await core.aprocess_request(
        request="Browse https://xeren.ai/docs and observe the active web page",
        context={"url": "https://xeren.ai/docs"},
        browser_adapter=mock_browser,
        verify_outcome=True,
        record_experience=True,
    )

    assert result["success"] is True
    plan = result["plan"]
    assert any(step.action_type in {"navigate", "observe", "extract"} for step in plan.steps)
    assert result["final_response"] != ""
    assert mock_browser.current_url == "https://xeren.ai/docs"


# =============================================================================
# Scenario 9: Failed Tool Execution
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_9_failed_tool_execution():
    """9. Validate structured non-silent failure handling when a plugin tool throws an error."""
    core = XerenCore(auto_register_defaults=True)

    # Force a failure by sending an invalid payload or non-existent file to data plugin
    exec_res = await core.aexecute_plugin(
        name="data",
        input_data={"operation": "inspect", "file_path": "non_existent_file_path_9999.csv"},
    )

    # Must fail gracefully with structured error info (no silent failure, no crash)
    assert exec_res.success is False
    assert exec_res.error is not None
    assert "not found" in exec_res.error.lower() or "failed" in exec_res.error.lower()
    assert exec_res.plugin_name == "data"


# =============================================================================
# Scenario 10: Failed Verification
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_10_failed_verification():
    """10. Validate that unsatisfied verification conditions produce verified=False and score=0.0."""
    core = XerenCore(auto_register_defaults=True)

    result = await core.aprocess_request(
        request="Research artificial intelligence architectures",
        context={"expected_conditions": ["contains impossible_mandatory_key_12345"]},
        verify_outcome=True,
        record_experience=True,
    )

    # Agent completed steps, but verification accurately caught the condition contradiction
    assert result["success"] is True
    verification = result["verification"]
    assert verification is not None
    assert verification.verified is False
    assert verification.score == 0.0

    # Experience record accurately flagged the verification failure
    experience = result["experience"]
    assert experience is not None
    assert experience.record.verification.verified is False


# =============================================================================
# Scenario 11: Permission-Required Action
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_11_permission_required_action():
    """11. Validate consequential actions are intercepted and denied without user approval."""
    core = XerenCore(auto_register_defaults=True)
    pm = PermissionManager(mode=PermissionMode.STRICT)

    # Upload action is classified as CONSEQUENTIAL and blocked in STRICT mode
    result = await core.aprocess_request(
        request="Upload confidential dataset to remote server",
        context={"file_path": "data.csv", "url": "https://example.com/upload"},
        permission_manager=pm,
        verify_outcome=True,
        record_experience=True,
    )

    # Task must fail safely due to permission denial
    assert result["success"] is False
    assert "permission" in result["final_response"].lower() or "failed" in result["final_response"].lower()


# =============================================================================
# Scenario 12: Invalid User Request
# =============================================================================

def test_scenario_12_invalid_user_request():
    """12. Validate pre-execution rejection of empty, malformed, or unsafe shell injection requests."""
    core = XerenCore(auto_register_defaults=True)
    planner = CorePlannerAdapter(plugin_manager=core.plugin_manager)

    # 1. Unsafe shell command injection blocked
    unsafe_plan = TaskPlan(
        goal="Clean system files",
        steps=[
            PlanStep(
                description="Run system purge",
                action_type="shell",
                target="rm -rf / --no-preserve-root",
            )
        ],
    )
    with pytest.raises(UnsafePlanError, match="prohibited execution pattern"):
        planner.validator.validate(unsafe_plan)

    # 2. Blank goal rejected
    blank_plan = TaskPlan(
        goal="   ",
        steps=[
            PlanStep(
                description="Valid step",
                action_type="navigate",
                target="https://example.com",
            )
        ],
    )
    with pytest.raises(PlanValidationError, match="non-empty user goal"):
        planner.validator.validate(blank_plan)


# =============================================================================
# Scenario 13: Agent Recovery and Replanning
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_13_agent_recovery_replanning():
    """13. Validate agent self-healing recovery and replanning upon step failure."""
    core = XerenCore(auto_register_defaults=True)
    planner = CorePlannerAdapter(plugin_manager=core.plugin_manager)

    # Initial plan with a failing step
    initial_plan = planner.create_task_plan(
        goal="Download report archive",
        context={"url": "https://example.com/download"},
    )
    assert len(initial_plan.steps) >= 2

    # Simulate dynamic replan upon step failure
    failed_step = initial_plan.steps[1]
    new_plan = await planner.areplan(
        failed_step=failed_step,
        error_message="Download button selector '#download-btn' not interactable",
        context={"alternative_url": "https://example.com/mirror"},
    )

    assert isinstance(new_plan, TaskPlan)
    assert len(new_plan.steps) > 0
    assert new_plan.metadata.get("replan_source_step") == failed_step.step_id
