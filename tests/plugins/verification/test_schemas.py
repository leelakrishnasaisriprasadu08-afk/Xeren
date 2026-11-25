"""Tests for Verification Plugin schemas, validation bounds, and default values."""

import pytest
from pydantic import ValidationError

from xeren.plugins.verification.schemas import (
    CandidateItem,
    CheckResult,
    EvidenceItem,
    JudgeVerdict,
    VerificationInput,
    VerificationOperation,
    VerificationResult,
    VerificationStatus,
)


def test_verification_status_values():
    """Verify all 4 required verification status enum members exist."""
    assert VerificationStatus.VERIFIED == "verified"
    assert VerificationStatus.PARTIALLY_VERIFIED == "partially_verified"
    assert VerificationStatus.FAILED == "failed"
    assert VerificationStatus.UNVERIFIABLE == "unverifiable"


def test_verification_operation_values():
    """Verify all 10 verification operation enum members exist."""
    assert VerificationOperation.OUTPUT_VALIDATION == "output_validation"
    assert VerificationOperation.FACT_CHECKING == "fact_checking"
    assert VerificationOperation.RESULT_RERANKING == "result_reranking"
    assert VerificationOperation.CONSISTENCY_CHECKING == "consistency_checking"
    assert VerificationOperation.CODE_VERIFICATION == "code_verification"
    assert VerificationOperation.DATA_VERIFICATION == "data_verification"
    assert VerificationOperation.SOURCE_EVIDENCE_CHECK == "source_evidence_check"
    assert VerificationOperation.CONFIDENCE_SCORING == "confidence_scoring"
    assert VerificationOperation.LLM_JUDGE == "llm_judge"
    assert VerificationOperation.FINAL_RESPONSE_VERIFICATION == "final_response_verification"


def test_evidence_item_schema():
    """Verify EvidenceItem fields, defaults, and bounds validation."""
    item = EvidenceItem(
        source_id="doc_1",
        content="Paris is the capital of France.",
        uri="https://example.com/paris",
        confidence=0.95,
    )
    assert item.source_id == "doc_1"
    assert item.content == "Paris is the capital of France."
    assert item.confidence == 0.95
    assert item.metadata == {}

    # Confidence must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        EvidenceItem(source_id="doc_2", content="text", confidence=1.5)

    with pytest.raises(ValidationError):
        EvidenceItem(source_id="doc_3", content="text", confidence=-0.1)


def test_candidate_item_schema():
    """Verify CandidateItem initialization, metadata, and score."""
    cand = CandidateItem(id="cand_1", content="Answer text", score=0.88)
    assert cand.id == "cand_1"
    assert cand.content == "Answer text"
    assert cand.score == 0.88
    assert cand.metadata == {}

    # Score bounds [0.0, 1.0]
    with pytest.raises(ValidationError):
        CandidateItem(id="cand_bad", content="text", score=1.2)


def test_check_result_schema():
    """Verify CheckResult fields and default score."""
    check = CheckResult(
        name="syntax_check",
        passed=True,
        score=1.0,
        reason="No syntax errors found.",
    )
    assert check.name == "syntax_check"
    assert check.passed is True
    assert check.score == 1.0
    assert check.actionable_correction is None
    assert check.details == {}


def test_judge_verdict_schema():
    """Verify JudgeVerdict fields and serialization."""
    verdict = JudgeVerdict(
        is_valid=True,
        score=0.9,
        rationale="Strong logical consistency and thorough reasoning.",
        criteria_scores={"accuracy": 1.0, "coherence": 0.8},
        suggested_improvements=["Condense conclusion section."],
    )
    assert verdict.is_valid is True
    assert verdict.score == 0.9
    assert len(verdict.suggested_improvements) == 1

    dumped = verdict.model_dump()
    assert dumped["is_valid"] is True
    assert dumped["criteria_scores"]["accuracy"] == 1.0


def test_verification_input_defaults():
    """Verify VerificationInput default operation and optional fields."""
    inp = VerificationInput(candidate="Sample output")
    assert inp.operation == VerificationOperation.FINAL_RESPONSE_VERIFICATION
    assert inp.candidate == "Sample output"
    assert inp.task is None
    assert inp.evidence == []
    assert inp.candidates == []
    assert inp.confidence_threshold == 0.70
    assert inp.strict_mode is False


def test_verification_result_serialization():
    """Verify VerificationResult model dumping and JSON compatibility."""
    res = VerificationResult(
        status=VerificationStatus.VERIFIED,
        operation=VerificationOperation.OUTPUT_VALIDATION,
        confidence_score=0.92,
        checks=[CheckResult(name="format_check", passed=True, score=1.0)],
        latency_ms=12.5,
    )
    dump = res.model_dump()
    assert dump["status"] == "verified"
    assert dump["operation"] == "output_validation"
    assert dump["confidence_score"] == 0.92
    assert dump["latency_ms"] == 12.5
    assert len(dump["checks"]) == 1
