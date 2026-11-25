"""Tests for SourceEvidenceTool (grounding, citations, unsupported claims, unverifiable status)."""

import pytest

from xeren.plugins.verification.schemas import EvidenceItem, VerificationOperation
from xeren.plugins.verification.tools.evidence import SourceEvidenceTool


@pytest.fixture
def evidence_tool():
    return SourceEvidenceTool()


def test_evidence_missing_fact_checking(evidence_tool):
    """Verify missing evidence in FACT_CHECKING triggers unverifiable flag and corrective action."""
    checks, score, prov, unsupp, is_unverifiable = evidence_tool.verify_evidence(
        candidate="The James Webb Telescope was launched on December 25, 2021.",
        evidence=[],
        operation=VerificationOperation.FACT_CHECKING,
    )
    assert is_unverifiable is True
    assert score == 0.0
    assert len(checks) == 1
    assert checks[0].name == "evidence_availability"
    assert checks[0].passed is False
    assert checks[0].actionable_correction is not None


def test_evidence_grounded_claims(evidence_tool):
    """Verify candidate matching evidence produces high grounding score and provenance links."""
    evidence = [
        EvidenceItem(
            source_id="nasa_doc_1",
            content="The James Webb Space Telescope was successfully launched on December 25, 2021 from French Guiana.",
            confidence=1.0,
        )
    ]
    candidate = "The James Webb Space Telescope was launched on December 25, 2021."

    checks, score, prov, unsupp, is_unverifiable = evidence_tool.verify_evidence(
        candidate=candidate,
        evidence=evidence,
        operation=VerificationOperation.FACT_CHECKING,
    )
    assert is_unverifiable is False
    assert score >= 0.70
    assert len(unsupp) == 0
    assert any("nasa_doc_1" in sources for sources in prov.values())

    ground_check = next(c for c in checks if c.name == "grounding_faithfulness_check")
    assert ground_check.passed is True


def test_evidence_unsupported_claim_detection(evidence_tool):
    """Verify unsupported claim detection flags hallucinated sentences."""
    evidence = [
        EvidenceItem(
            source_id="ev_solar",
            content="Mercury is the smallest planet in the solar system and closest to the Sun.",
            confidence=1.0,
        )
    ]
    candidate = (
        "Mercury is the smallest planet in the solar system. "
        "It contains vast subterranean liquid water oceans supporting microbial life."
    )

    checks, score, prov, unsupp, is_unverifiable = evidence_tool.verify_evidence(
        candidate=candidate,
        evidence=evidence,
        operation=VerificationOperation.FACT_CHECKING,
    )
    assert is_unverifiable is False
    assert len(unsupp) >= 1
    assert any("liquid water oceans" in s for s in unsupp)

    unsupp_check = next(c for c in checks if c.name == "unsupported_claims_check")
    assert unsupp_check.passed is False
    assert unsupp_check.actionable_correction is not None


def test_evidence_citation_validation(evidence_tool):
    """Verify citation validation accepts real sources and rejects hallucinated ones."""
    evidence = [
        EvidenceItem(source_id="source_a", content="Data for source A.", confidence=1.0),
        EvidenceItem(source_id="source_b", content="Data for source B.", confidence=1.0),
    ]

    # Valid citations
    text_valid = "According to [source_a], this is confirmed. Additional details in [source_b]."
    checks_v, _, _, _, _ = evidence_tool.verify_evidence(
        candidate=text_valid,
        evidence=evidence,
        operation=VerificationOperation.SOURCE_EVIDENCE_CHECK,
    )
    cit_v = next(c for c in checks_v if c.name == "citation_validity_check")
    assert cit_v.passed is True

    # Hallucinated citation
    text_invalid = "This conclusion is proven by [source_fake_999]."
    checks_inv, _, _, _, _ = evidence_tool.verify_evidence(
        candidate=text_invalid,
        evidence=evidence,
        operation=VerificationOperation.SOURCE_EVIDENCE_CHECK,
    )
    cit_inv = next(c for c in checks_inv if c.name == "citation_validity_check")
    assert cit_inv.passed is False
    assert "source_fake_999" in str(cit_inv.reason)
    assert cit_inv.actionable_correction is not None
