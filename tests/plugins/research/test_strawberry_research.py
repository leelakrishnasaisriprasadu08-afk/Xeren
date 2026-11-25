"""Unit tests for Strawberry AI research planner, credibility scoring, and cross-verification."""

from __future__ import annotations

import pytest

from xeren.plugins.research.tools.strawberry_planner import StrawberryQueryPlanner
from xeren.plugins.research.tools.credibility_scorer import CredibilityScorer
from xeren.plugins.research.tools.claim_verifier import ClaimVerifier, ClaimStatus
from xeren.security.schemas import DomainTier


class TestStrawberryQueryPlanner:
    def test_multi_angle_plan_generation(self):
        planner = StrawberryQueryPlanner()
        plan = planner.create_plan("Solid State Batteries in EV", depth="deep")

        assert len(plan.angles) >= 3
        angle_types = {a.angle_type for a in plan.angles}
        assert "factual" in angle_types
        assert "counterfactual" in angle_types
        assert "statistical" in angle_types

    def test_sensitive_leak_sanitization(self):
        planner = StrawberryQueryPlanner()
        raw_topic = "Verify user Aadhaar 1234 5678 9012 and secret password123 on solid batteries"
        plan = planner.create_plan(raw_topic)

        for angle in plan.angles:
            assert "1234 5678 9012" not in angle.query
            assert "password123" not in angle.query
            assert "[REDACTED]" in angle.query


class TestCredibilityScorer:
    def test_authoritative_domains(self):
        scorer = CredibilityScorer()
        rep_gov = scorer.evaluate_url("https://www.nist.gov/cybersecurity/framework")
        assert rep_gov.tier == DomainTier.AUTHORITY
        assert rep_gov.credibility_score >= 0.90
        assert rep_gov.is_safe

        rep_arxiv = scorer.evaluate_url("https://arxiv.org/abs/2301.00001")
        assert rep_arxiv.tier == DomainTier.AUTHORITY

    def test_trusted_news(self):
        scorer = CredibilityScorer()
        rep = scorer.evaluate_url("https://www.reuters.com/technology/quantum-leap-2026")
        assert rep.tier == DomainTier.TRUSTED_NEWS
        assert rep.credibility_score >= 0.85

    def test_suspicious_harmful_patterns(self):
        scorer = CredibilityScorer()
        rep = scorer.evaluate_url("http://crypto-giveaway-claim-airdrop.xyz/login-verify")
        assert not rep.is_safe
        assert rep.credibility_score <= 0.20


class TestClaimVerifier:
    def test_claim_verified_with_concurring_authorities(self):
        verifier = ClaimVerifier()
        evidence = [
            {"url": "https://www.nature.com/articles/s41586-battery", "excerpt": "Solid state achieved 80% charge in 10 mins.", "supports": True},
            {"url": "https://www.nist.gov/reports/ev-battery", "excerpt": "Lab testing confirmed 10 min benchmark.", "supports": True},
        ]
        result = verifier.verify_claim("Solid-state batteries achieve 10-minute fast charging", evidence)
        assert result.status == ClaimStatus.VERIFIED
        assert result.confidence > 0.85

    def test_claim_contested_when_sources_disagree(self):
        verifier = ClaimVerifier()
        evidence = [
            {"url": "https://www.reuters.com/tech-news", "excerpt": "Study says tech is commercially ready.", "supports": True},
            {"url": "https://www.scientificamerican.com/critique", "excerpt": "Thermal stability issues prevent mass adoption.", "supports": False},
        ]
        result = verifier.verify_claim("Solid-state batteries are ready for mass market rollout", evidence)
        assert result.status == ClaimStatus.CONTESTED
        assert result.confidence == 0.50
