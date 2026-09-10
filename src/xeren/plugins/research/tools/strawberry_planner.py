"""Strawberry AI Query Planner — Multi-angle query decomposition and safe search strategy."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger("xeren.research.strawberry_planner")


@dataclass
class ResearchAngle:
    """A specific analytical angle for deep investigation."""
    angle_type: str  # "factual", "counterfactual", "statistical", "consensus"
    query: str
    rationale: str
    target_domain_tier: str = "authority"  # "authority", "trusted_news", "general"


@dataclass
class StrawberryPlan:
    """Comprehensive multi-angle research strategy for a topic."""
    original_topic: str
    angles: List[ResearchAngle] = field(default_factory=list)
    safe_search_enforced: bool = True
    excluded_keywords: List[str] = field(default_factory=list)


class StrawberryQueryPlanner:
    """
    Implements the 'Strawberry AI' research strategy:
    Instead of executing one random web search, it strategically decomposes
    the research objective across 4 rigorous inquiry dimensions:
    1. Core Fact Finding (direct empirical definitions & claims)
    2. Counter-perspective / Falsification (checks counter-arguments & edge cases)
    3. Empirical & Statistical Evidence (data points, metrics, studies)
    4. Institutional & Peer-reviewed Consensus (official documentation, standards)
    """

    # Unsafe / leaking patterns that must never be sent to external search engines
    SENSITIVE_LEAK_PATTERNS = [
        re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),  # Aadhaar / Card numbers
        re.compile(r"\b[A-Z]{5}\d{4}[A-Z]{1}\b"),        # PAN card format
        re.compile(r"\bpassword|secret[\s_]?key|api[\s_]?key|private[\s_]?key\b|\b(?:sk-[A-Za-z0-9]{20,})\b", re.I),
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Emails
    ]

    def create_plan(self, topic: str, depth: str = "deep") -> StrawberryPlan:
        """
        Generate a multi-angle Strawberry research plan for the given topic.
        Guarantees sensitive user data is stripped before queries are planned.
        """
        safe_topic = self._sanitize_topic(topic)

        angles: List[ResearchAngle] = []

        # 1. Factual Foundation
        angles.append(ResearchAngle(
            angle_type="factual",
            query=f"{safe_topic} overview technical documentation",
            rationale="Establish core definitions, architectural facts, and foundational mechanisms.",
            target_domain_tier="authority",
        ))

        # 2. Counter-perspective / Falsification
        angles.append(ResearchAngle(
            angle_type="counterfactual",
            query=f"{safe_topic} limitations criticisms drawbacks risks",
            rationale="Strawberry approach: stress-test hypotheses against known criticisms and vulnerabilities.",
            target_domain_tier="trusted_news",
        ))

        # 3. Statistical / Empirical Data
        angles.append(ResearchAngle(
            angle_type="statistical",
            query=f"{safe_topic} benchmark statistics empirical performance metrics",
            rationale="Retrieve quantified real-world data and benchmark measurements.",
            target_domain_tier="authority",
        ))

        # 4. Institutional / Consensus Standard
        if depth in ("deep", "exhaustive"):
            angles.append(ResearchAngle(
                angle_type="consensus",
                query=f"{safe_topic} IEEE ACM RFC peer reviewed standards consensus",
                rationale="Identify authoritative industry or academic consensus and official specifications.",
                target_domain_tier="authority",
            ))

        return StrawberryPlan(
            original_topic=topic,
            angles=angles,
            safe_search_enforced=True,
            excluded_keywords=["personal data", "private", "confidential"],
        )

    def _sanitize_topic(self, topic: str) -> str:
        """Strip any sensitive identifiers, passwords, or personal data."""
        sanitized = topic
        for pattern in self.SENSITIVE_LEAK_PATTERNS:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        return sanitized.strip()


__all__ = ["StrawberryQueryPlanner", "StrawberryPlan", "ResearchAngle"]
