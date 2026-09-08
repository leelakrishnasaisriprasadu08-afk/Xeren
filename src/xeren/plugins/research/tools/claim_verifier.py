"""ClaimVerifier — Multi-source cross-verification matrix for research claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

from xeren.plugins.research.tools.credibility_scorer import CredibilityScorer, CredibilityReport


class ClaimStatus(str, Enum):
    VERIFIED = "verified"          # Backed by 2+ credible sources
    CONTESTED = "contested"        # Sources contradict each other
    UNVERIFIED = "unverified"      # Only single or low-credibility source
    REFUTED = "refuted"            # Debunked by high-authority source


@dataclass
class EvidencePoint:
    source_url: str
    credibility: float
    excerpt: str
    supports_claim: bool = True


@dataclass
class VerifiedClaim:
    claim_text: str
    status: ClaimStatus
    confidence: float
    evidence: List[EvidencePoint] = field(default_factory=list)
    consensus_summary: str = ""


class ClaimVerifier:
    """
    Constructs a multi-source cross-verification matrix.
    Prevents hallucination and erroneous web results by requiring
    cross-corroboration between distinct authoritative sources.
    """

    def __init__(self, credibility_scorer: CredibilityScorer | None = None) -> None:
        self.scorer = credibility_scorer or CredibilityScorer()

    def verify_claim(self, claim_text: str, source_evidence: List[Dict[str, Any]]) -> VerifiedClaim:
        """
        Evaluate a claim against multiple sources.

        Args:
            claim_text: The factual assertion.
            source_evidence: List of dicts with keys 'url', 'excerpt', 'supports' (bool).
        """
        evidence_points: List[EvidencePoint] = []
        supporting_weight = 0.0
        opposing_weight = 0.0

        for item in source_evidence:
            url = item.get("url", "")
            supports = item.get("supports", True)
            excerpt = item.get("excerpt", "")

            report = self.scorer.evaluate_url(url)
            weight = report.credibility_score

            evidence_points.append(EvidencePoint(
                source_url=url,
                credibility=weight,
                excerpt=excerpt,
                supports_claim=supports,
            ))

            if supports:
                supporting_weight += weight
            else:
                opposing_weight += weight

        # Status determination logic
        if supporting_weight >= 1.7 and opposing_weight == 0.0:
            status = ClaimStatus.VERIFIED
            confidence = min(0.98, supporting_weight / (supporting_weight + 0.2))
            summary = "Corroborated by multiple high-credibility sources with no recorded dissent."
        elif opposing_weight > 0.0 and supporting_weight > 0.0:
            status = ClaimStatus.CONTESTED
            confidence = 0.50
            summary = "Conflicting evidence found across sources; consensus is split."
        elif opposing_weight >= 1.5:
            status = ClaimStatus.REFUTED
            confidence = 0.90
            summary = "Refuted by authoritative counter-evidence."
        else:
            status = ClaimStatus.UNVERIFIED
            confidence = 0.40
            summary = "Single or unverified source; pending further corroboration."

        return VerifiedClaim(
            claim_text=claim_text,
            status=status,
            confidence=confidence,
            evidence=evidence_points,
            consensus_summary=summary,
        )


__all__ = ["ClaimVerifier", "VerifiedClaim", "ClaimStatus", "EvidencePoint"]
