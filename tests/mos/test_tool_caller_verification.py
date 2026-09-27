"""Tests for ToolCaller as Work Assigner & Output Verifier (JEPA/Discriminator Architecture)."""

import pytest
from backend.automation_framework.mos.protocol import (
    AssignmentExpectation,
    DispatchRequest,
    SpecialistResult,
    SpecialistTask,
    TaskStatus,
)
from backend.automation_framework.mos.tool_caller import ToolCaller
from backend.automation_framework.mos.specialist_runner import SpecialistRunner


def test_work_assigner_phase():
    """Verify Phase 1: Work Assigner produces structured assignment without conversational bloat."""
    tool_caller = ToolCaller()
    req = DispatchRequest(
        user_query="Write a Python script to calculate Fibonacci sequence and verify its time complexity",
        task_description="Implement Fibonacci and analyze time complexity",
        required_capabilities=["coding", "analysis"],
        allow_parallel=True,
    )

    plan = tool_caller.assign(req)
    assert plan.is_executable is True
    assert plan.execution_strategy == "parallel"
    assert len(plan.assignments) >= 2
    assert plan.confidence >= 0.85

    # Check assignment details
    coding_assignment = next(a for a in plan.assignments if "coding" in a.specialist_id)
    assert coding_assignment.action == "implement_code"
    assert coding_assignment.expectation.format == "code"
    assert coding_assignment.expectation.syntax_check is True
    assert coding_assignment.confidence >= 0.85


def test_output_verifier_success():
    """Verify Phase 2: Output Verifier validates compliant deliverable with booleans & confidence."""
    tool_caller = ToolCaller()
    task = SpecialistTask(
        specialist_id="M7_coding",
        sub_task="Write python factorial",
        expected_output_format="code",
        expectation=AssignmentExpectation(format="code", syntax_check=True, non_empty=True),
    )
    result = SpecialistResult(
        specialist_id="M7_coding",
        status=TaskStatus.SUCCESS,
        output="def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n",
        confidence=0.99,
        execution_ms=15.0,
    )

    verdict = tool_caller.verify(task, result)
    assert verdict.passed is True
    assert verdict.expectations_met is True
    assert verdict.syntax_valid is True
    assert verdict.has_error is False
    assert verdict.needs_retry is False
    assert verdict.confidence >= 0.95
    assert verdict.score == 1.0


def test_output_verifier_syntax_error_detection():
    """Verify Output Verifier catches syntax errors, flags needs_retry, and provides diagnosis."""
    tool_caller = ToolCaller()
    task = SpecialistTask(
        specialist_id="M7_coding",
        sub_task="Write python broken code",
        expected_output_format="code",
        expectation=AssignmentExpectation(format="code", syntax_check=True, non_empty=True),
    )
    # Deliberate Python syntax error: missing colon
    result = SpecialistResult(
        specialist_id="M7_coding",
        status=TaskStatus.SUCCESS,
        output="def broken_func(a, b)\n    return a + b\n",
        confidence=0.90,
    )

    verdict = tool_caller.verify(task, result)
    assert verdict.passed is False
    assert verdict.syntax_valid is False
    assert verdict.expectations_met is False
    assert verdict.has_error is True
    assert verdict.needs_retry is True
    assert "SYNTAX_ERROR" in verdict.error_type
    assert "fix_syntax_at_line" in verdict.retry_adjustments


def test_output_verifier_json_schema_error():
    """Verify Output Verifier catches invalid JSON output when json format is expected."""
    tool_caller = ToolCaller()
    task = SpecialistTask(
        specialist_id="M5_analysis",
        sub_task="Analyze data distribution",
        expected_output_format="json",
        expectation=AssignmentExpectation(format="json", required_keys=["result"], syntax_check=True),
    )
    # Broken JSON string
    result = SpecialistResult(
        specialist_id="M5_analysis",
        status=TaskStatus.SUCCESS,
        output="This is plain text not a json object {invalid",
    )

    verdict = tool_caller.verify(task, result)
    assert verdict.passed is False
    assert verdict.syntax_valid is False
    assert verdict.needs_retry is True
    assert "INVALID_JSON" in verdict.error_type


@pytest.mark.asyncio
async def test_full_pipeline_with_automatic_verification():
    """Verify end-to-end dispatch runs assign -> execute -> verify automatically."""
    runner = SpecialistRunner(main_llm=None)  # STUB mode
    tool_caller = ToolCaller(runner=runner)

    req = DispatchRequest(
        user_query="Solve this math puzzle and write a verification script",
        task_description="Solve puzzle and write verification",
        required_capabilities=["reasoning", "coding"],
        allow_parallel=True,
    )

    resp = await tool_caller.dispatch(req)
    assert resp.status == TaskStatus.SUCCESS
    assert resp.all_passed is True
    assert resp.overall_confidence >= 0.90
    assert len(resp.verification_verdicts) >= 2
    for v in resp.verification_verdicts:
        assert v.passed is True
        assert v.has_error is False
