"""
Tests for ToolCaller & Sovereign Pattern DB Integration.
========================================================
Validates:
1. Pre-emptive security policy enforcement via PatternCorner.RULES_PERMISSIONS
2. Sovereign Temperature Spectrum assignment (T=0.0 automation vs T>=1.0 creative)
3. PatternCorner.FAILURE_FIX automatic retrieval and retry prompt augmentation
4. Successful execution trace ingestion into PatternCorner.INTENT_SOLUTION
"""
import pytest
from unittest.mock import MagicMock

from backend.automation_framework.mos.protocol import (
    AssignmentExpectation,
    DispatchRequest,
    SpecialistResult,
    SpecialistTask,
    TaskAssignment,
    TaskStatus,
)
from backend.automation_framework.mos.specialist_registry import SpecialistID
from backend.automation_framework.mos.specialist_runner import SpecialistRunner
from backend.automation_framework.mos.tool_caller import ToolCaller
from xeren.rag.stores.pattern_db.corners.models import PatternCorner
from xeren.rag.stores.pattern_db.engine import XerenPatternDB


class TestToolCallerPatternDBIntegration:
    """Test suite for MoS ToolCaller + Sovereign Pattern DB bridge."""

    @pytest.fixture
    def pattern_db(self):
        """Create fresh in-memory Sovereign Pattern DB."""
        return XerenPatternDB()

    def test_security_rules_pre_check_blocks_prohibited_action(self, pattern_db):
        """Verify that a prohibited rule in RULES_PERMISSIONS stops execution before dispatch."""
        # 1. Ingest an explicit prohibition rule
        pattern_db.ingest_corner_pattern(
            corner=PatternCorner.RULES_PERMISSIONS,
            raw_data={
                "subject": "automation_specialist",
                "action": "delete system files",
                "resource": "system_drive",
                "allowed": False,
            },
            summary="Automation specialists are forbidden from deleting system files or formatting drives",
            success=True,
        )

        tool_caller = ToolCaller(pattern_db=pattern_db)

        req = DispatchRequest(
            user_query="Please delete system files from the drive",
            task_description="delete system files to free up disk space",
            required_capabilities=["code"],
        )

        plan = tool_caller.assign(req)

        assert plan.is_executable is False
        assert "SECURITY_PERMISSION_DENIED" in plan.reason_code
        assert len(plan.assignments) == 0

    def test_temperature_spectrum_inference(self):
        """Verify temperature spectrum allocates T=0.0 for automation and T>=1.0 for creative."""
        tool_caller = ToolCaller()

        assert tool_caller._infer_temperature("tool_caller") == 0.0
        assert tool_caller._infer_temperature("M0_tool_caller") == 0.0
        assert tool_caller._infer_temperature("M7_coding") == 0.0
        assert tool_caller._infer_temperature("M10_verification") == 0.0
        assert tool_caller._infer_temperature("M14_security") == 0.0

        assert tool_caller._infer_temperature("M2_reasoning") == 0.2
        assert tool_caller._infer_temperature("M13_creative") >= 1.0

        # Verify task builder sets temperature
        req = DispatchRequest(
            user_query="Write a creative poem",
            task_description="compose a creative poem about space",
        )
        assignment = TaskAssignment(
            specialist_id="M13_creative",
            action="compose_story",
            arguments={},
            expectation=AssignmentExpectation(),
            confidence=0.9,
            priority=1,
        )
        task = tool_caller._build_task_from_assignment(req, assignment)
        assert task.temperature == 1.0

    def test_output_verifier_injects_proven_failure_fix(self, pattern_db):
        """Verify that verification failures pull historical fixes from FAILURE_FIX corner."""
        # Ingest known failure fix into Pattern DB
        pattern_db.ingest_corner_pattern(
            corner=PatternCorner.FAILURE_FIX,
            raw_data={
                "error": "SYNTAX_ERROR: expected ':'",
                "fix": "Ensure all def and if blocks terminate with a colon ':' and valid indent",
            },
            summary="Fix missing colon syntax error in Python function definition",
            success=True,
        )

        tool_caller = ToolCaller(pattern_db=pattern_db)

        task = SpecialistTask(
            specialist_id="M7_coding",
            specialist_name="M7 — Coding",
            sub_task="Write python function",
            expected_output_format="code",
            expectation=AssignmentExpectation(format="code", syntax_check=True),
        )

        broken_result = SpecialistResult(
            task_trace_id=task.trace_id,
            specialist_id=task.specialist_id,
            status=TaskStatus.SUCCESS,
            output="def calculate(x)\n    return x * 2",  # Missing colon
            confidence=0.5,
            execution_ms=12.0,
        )

        verdict = tool_caller.verify(task, broken_result)

        assert verdict.passed is False
        assert verdict.needs_retry is True
        assert "proven_fix" in verdict.retry_adjustments
        assert "Ensure all def and if blocks terminate with a colon" in verdict.retry_adjustments["proven_fix"]

        # Check that retry task includes the proven fix in the prompt
        retry_task = tool_caller._build_retry_task(task, verdict)
        assert "[PROVEN HISTORICAL FIX]" in retry_task.sub_task
        assert "Ensure all def and if blocks terminate with a colon" in retry_task.sub_task

    @pytest.mark.asyncio
    async def test_successful_dispatch_ingests_intent_solution(self, pattern_db):
        """Verify that successful multi-specialist runs record traces into INTENT_SOLUTION."""
        # Use stub runner so execution succeeds cleanly
        runner = SpecialistRunner(force_mode="STUB")
        tool_caller = ToolCaller(pattern_db=pattern_db, runner=runner)

        req = DispatchRequest(
            user_query="Create deployment manifest",
            task_description="Create deployment manifest for kubernetes pod",
            required_capabilities=["plan"],
        )

        response = await tool_caller.dispatch(req)
        assert response.status == TaskStatus.SUCCESS
        assert response.all_passed is True

        # Check INTENT_SOLUTION partition in PatternDB
        records = pattern_db._corner_store._partitions[PatternCorner.INTENT_SOLUTION]
        assert len(records) >= 1
        top_rec = records[0]
        assert "Create deployment manifest" in top_rec.raw["task_description"]
        assert top_rec.trust_score == 1.0
