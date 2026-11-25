"""CredibilityScorer — Evaluates web sources for authenticity, bias, and authority."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from xeren.security.schemas import DomainTier


@dataclass
class CredibilityReport:
    """Credibility assessment for a source URL."""
    url: str
    domain: str
    tier: DomainTier
    credibility_score: float  # 0.0 to 1.0
    is_safe: bool
    notes: str


class CredibilityScorer:
    """
    Evaluates web domains and URLs to protect users from malicious sites
    and ensure research is grounded in verified, authoritative sources.
    """

    AUTHORITY_DOMAINS = {
        "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org",
        "nih.gov", "who.int", "nasa.gov", "cdc.gov", "nist.gov",
        "w3.org", "ietf.org", "python.org", "docs.python.org", "github.com",
    }

    TRUSTED_NEWS_DOMAINS = {
        "reuters.com", "apnews.com", "bbc.com", "bloomberg.com", "nytimes.com",
        "wsj.com", "theguardian.com", "nature.com", "scientificamerican.com",
        "arstechnica.com", "wikipedia.org",
    }

    SUSPICIOUS_PATTERNS = [
        re.compile(r"free-download|crack|keygen|crypto-giveaway|claim-airdrop", re.I),
        re.compile(r"\b(phishing|login-verify|account-update-alert)\b", re.I),
        re.compile(r"\.(xyz|top|work|click|loan|stream|date)$", re.I),
    ]

    def evaluate_url(self, url: str) -> CredibilityReport:
        """Analyze a URL and calculate a credibility score."""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = (parsed.netloc or "").lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            return CredibilityReport(
                url=url,
                domain="unknown",
                tier=DomainTier.COMMERCIAL,
                credibility_score=0.2,
                is_safe=False,
                notes="Malformed URL.",
            )

        # 1. Check for malicious / suspicious patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.search(url) or pattern.search(domain):
                return CredibilityReport(
                    url=url,
                    domain=domain,
                    tier=DomainTier.COMMERCIAL,
                    credibility_score=0.1,
                    is_safe=False,
                    notes="Flagged for suspicious/harmful keywords or high-risk TLD.",
                )

        # 2. Check for Top-Level Academic / Government Domains
        if domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".mil"):
            return CredibilityReport(
                url=url,
                domain=domain,
                tier=DomainTier.AUTHORITY,
                credibility_score=0.98,
                is_safe=True,
                notes="Authoritative government or educational institution domain.",
            )

        # 3. Known Authority Domains
        if domain in self.AUTHORITY_DOMAINS:
            return CredibilityReport(
                url=url,
                domain=domain,
                tier=DomainTier.AUTHORITY,
                credibility_score=0.95,
                is_safe=True,
                notes="Recognized scientific or official documentation authority.",
            )

        # 4. Known Trusted News / Reference
        if domain in self.TRUSTED_NEWS_DOMAINS:
            return CredibilityReport(
                url=url,
                domain=domain,
                tier=DomainTier.TRUSTED_NEWS,
                credibility_score=0.88,
                is_safe=True,
                notes="Established editorial journalism or broad reference repository.",
            )

        # 5. General / Commercial Web
        return CredibilityReport(
            url=url,
            domain=domain,
            tier=DomainTier.COMMERCIAL,
            credibility_score=0.65,
            is_safe=True,
            notes="General web source; cross-verification recommended.",
        )


__all__ = ["CredibilityScorer", "CredibilityReport"]
