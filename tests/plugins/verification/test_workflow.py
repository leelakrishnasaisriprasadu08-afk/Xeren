"""Tests for VerificationWorkflow dispatching all 10 verification operations."""

import pytest

from xeren.plugins.verification.schemas import (
    CandidateItem,
    EvidenceItem,
    VerificationInput,
    VerificationOperation,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.verification.workflow import VerificationWorkflow


@pytest.fixture
def workflow():
    return VerificationWorkflow()


def test_workflow_output_validation(workflow):
    """Verify OUTPUT_VALIDATION operation execution."""
    inp = VerificationInput(
        operation=VerificationOperation.OUTPUT_VALIDATION,
        candidate='{"status": "success", "count": 10}',
        expected_format="json",
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.OUTPUT_VALIDATION
    assert res.status == VerificationStatus.VERIFIED
    assert res.latency_ms >= 0.0


def test_workflow_fact_checking_with_evidence(workflow):
    """Verify FACT_CHECKING operation with provided evidence."""
    evidence = [
        EvidenceItem(source_id="s1", content="Xeren is an autonomous AI agent framework.", confidence=1.0)
    ]
    inp = VerificationInput(
        operation=VerificationOperation.FACT_CHECKING,
        candidate="Xeren is an autonomous AI agent framework with pluggable architecture.",
        evidence=evidence,
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.FACT_CHECKING
    assert res.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)
    assert res.evidence_grounding_score is not None


def test_workflow_fact_checking_without_evidence_unverifiable(workflow):
    """Verify FACT_CHECKING operation without evidence yields UNVERIFIABLE status."""
    inp = VerificationInput(
        operation=VerificationOperation.FACT_CHECKING,
        candidate="Some claim without evidence",
        evidence=[],
    )
    res = workflow.run(inp)
    assert res.status == VerificationStatus.UNVERIFIABLE
    assert res.confidence_score == 0.0
    assert len(res.actionable_corrections) >= 1


def test_workflow_result_reranking(workflow):
    """Verify RESULT_RERANKING operation orders candidates."""
    candidates = [
        CandidateItem(id="low", content="General greeting"),
        CandidateItem(id="high", content="Specific detailed explanation of algorithm time complexity"),
    ]
    inp = VerificationInput(
        operation=VerificationOperation.RESULT_RERANKING,
        candidates=candidates,
        task="Explain the algorithm time complexity in detail",
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.RESULT_RERANKING
    assert res.reranked_candidates is not None
    assert res.reranked_candidates[0].id == "high"


def test_workflow_consistency_checking(workflow):
    """Verify CONSISTENCY_CHECKING operation detects internal alignment."""
    inp = VerificationInput(
        operation=VerificationOperation.CONSISTENCY_CHECKING,
        candidate="The query completed in 45ms. Database performance was optimal.",
        task="Check database performance",
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.CONSISTENCY_CHECKING
    assert res.status == VerificationStatus.VERIFIED
    assert res.consistency_score is not None


def test_workflow_code_verification(workflow):
    """Verify CODE_VERIFICATION operation on Python code."""
    valid_py = "def multiply(x: int, y: int) -> int:\n    return x * y\n"
    inp = VerificationInput(
        operation=VerificationOperation.CODE_VERIFICATION,
        candidate=valid_py,
        task="Implement multiplication",
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.CODE_VERIFICATION
    assert res.status == VerificationStatus.VERIFIED


def test_workflow_data_verification(workflow):
    """Verify DATA_VERIFICATION operation on structured datasets."""
    dataset = [
        {"timestamp": "2025-01-01T00:00:00Z", "metric": 99.2},
        {"timestamp": "2025-01-01T01:00:00Z", "metric": 98.7},
    ]
    inp = VerificationInput(
        operation=VerificationOperation.DATA_VERIFICATION,
        candidate=dataset,
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.DATA_VERIFICATION
    assert res.status == VerificationStatus.VERIFIED


def test_workflow_source_evidence_check(workflow):
    """Verify SOURCE_EVIDENCE_CHECK operation."""
    evidence = [EvidenceItem(source_id="ref1", content="Quantum supremacy achieved.", confidence=1.0)]
    inp = VerificationInput(
        operation=VerificationOperation.SOURCE_EVIDENCE_CHECK,
        candidate="Quantum supremacy was achieved according to experiments.",
        evidence=evidence,
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.SOURCE_EVIDENCE_CHECK
    assert res.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)


def test_workflow_confidence_scoring(workflow):
    """Verify CONFIDENCE_SCORING operation calculates composite score."""
    inp = VerificationInput(
        operation=VerificationOperation.CONFIDENCE_SCORING,
        candidate="Clear answer to the user prompt.",
        task="Answer user prompt",
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.CONFIDENCE_SCORING
    assert res.confidence_score > 0.0


def test_workflow_llm_judge(workflow):
    """Verify LLM_JUDGE operation invokes configured judge evaluator."""
    inp = VerificationInput(
        operation=VerificationOperation.LLM_JUDGE,
        candidate="This response solves the requested task cleanly.",
        task="Solve the task",
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.LLM_JUDGE
    assert res.judge_verdict is not None
    assert res.judge_verdict.is_valid is True


def test_workflow_final_response_verification(workflow):
    """Verify FINAL_RESPONSE_VERIFICATION full multi-stage pipeline."""
    evidence = [EvidenceItem(source_id="wiki", content="Python was created by Guido van Rossum.", confidence=1.0)]
    inp = VerificationInput(
        operation=VerificationOperation.FINAL_RESPONSE_VERIFICATION,
        candidate="Python was created by Guido van Rossum and released in 1991.",
        task="Who created Python?",
        evidence=evidence,
    )
    res = workflow.run(inp)
    assert res.operation == VerificationOperation.FINAL_RESPONSE_VERIFICATION
    assert res.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)
    assert res.confidence_score > 0.6
    assert res.judge_verdict is not None
    assert len(res.checks) >= 3


@pytest.mark.asyncio
async def test_workflow_arun(workflow):
    """Verify asynchronous workflow execution."""
    inp = VerificationInput(
        operation=VerificationOperation.FINAL_RESPONSE_VERIFICATION,
        candidate="Asynchronous verification pipeline test.",
        task="Test async pipeline",
    )
    res = await workflow.arun(inp)
    assert isinstance(res, VerificationResult)
    assert res.latency_ms >= 0.0
