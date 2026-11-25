"""Tests for ConfidenceScorerTool (status calibration, multi-signal weighting, failure aggregation)."""

import pytest

from xeren.plugins.verification.schemas import (
    CheckResult,
    JudgeVerdict,
    VerificationOperation,
    VerificationStatus,
)
from xeren.plugins.verification.tools.confidence import ConfidenceScorerTool


@pytest.fixture
def scorer():
    return ConfidenceScorerTool()


def test_confidence_unverifiable(scorer):
    """Verify is_unverifiable=True results in UNVERIFIABLE status and score 0.0."""
    checks = [
        CheckResult(
            name="evidence_availability",
            passed=False,
            score=0.0,
            reason="No source evidence available.",
            actionable_correction="Provide retrieved documents.",
        )
    ]
    status, conf, fails, fixes = scorer.score(
        checks=checks,
        is_unverifiable=True,
        operation=VerificationOperation.FACT_CHECKING,
    )
    assert status == VerificationStatus.UNVERIFIABLE
    assert conf == 0.0
    assert len(fails) >= 1
    assert "Provide retrieved documents." in fixes


def test_confidence_fatal_structural_failure(scorer):
    """Verify fatal structural failure forces FAILED status and low confidence cap."""
    checks = [
        CheckResult(
            name="python_syntax_check",
            passed=False,
            score=0.0,
            reason="SyntaxError near line 3.",
            actionable_correction="Fix syntax error.",
        )
    ]
    judge = JudgeVerdict(is_valid=True, score=0.9, rationale="Conceptually looks fine.")

    status, conf, fails, fixes = scorer.score(
        checks=checks,
        judge_verdict=judge,
        confidence_threshold=0.70,
    )
    assert status == VerificationStatus.FAILED
    assert conf <= 0.25
    assert any("SyntaxError" in r for r in fails)
    assert "Fix syntax error." in fixes


def test_confidence_verified_status(scorer):
    """Verify clean passing checks and high scores yield VERIFIED status."""
    checks = [
        CheckResult(name="non_empty_check", passed=True, score=1.0),
        CheckResult(name="json_format_check", passed=True, score=1.0),
    ]
    judge = JudgeVerdict(is_valid=True, score=0.95, rationale="Excellent output.")

    status, conf, fails, fixes = scorer.score(
        checks=checks,
        judge_verdict=judge,
        grounding_score=0.90,
        consistency_score=1.0,
        confidence_threshold=0.70,
    )
    assert status == VerificationStatus.VERIFIED
    assert conf >= 0.85
    assert len(fails) == 0


def test_confidence_partially_verified(scorer):
    """Verify moderate score without fatal syntax failure yields PARTIALLY_VERIFIED."""
    checks = [
        CheckResult(name="non_empty_check", passed=True, score=1.0),
        CheckResult(
            name="schema_required_fields_check",
            passed=False,
            score=0.5,
            reason="Missing optional address field.",
            actionable_correction="Add address object.",
        ),
    ]
    judge = JudgeVerdict(is_valid=True, score=0.65, rationale="Mostly complete response.")

    status, conf, fails, fixes = scorer.score(
        checks=checks,
        judge_verdict=judge,
        confidence_threshold=0.75,
        strict_mode=False,
    )
    assert status == VerificationStatus.PARTIALLY_VERIFIED
    assert 0.40 <= conf < 0.75
    assert len(fails) >= 1
    assert "Add address object." in fixes


def test_confidence_strict_mode(scorer):
    """Verify strict_mode=True forces FAILED on any check failure."""
    checks = [
        CheckResult(name="non_empty_check", passed=True, score=1.0),
        CheckResult(
            name="citation_validity_check",
            passed=False,
            score=0.8,
            reason="Citation marker format minor warning.",
            actionable_correction="Standardize citation format.",
        ),
    ]
    status, conf, fails, fixes = scorer.score(
        checks=checks,
        confidence_threshold=0.70,
        strict_mode=True,
    )
    assert status == VerificationStatus.FAILED
