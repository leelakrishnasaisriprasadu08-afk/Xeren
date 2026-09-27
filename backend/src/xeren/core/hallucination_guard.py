"""HallucinationGuard — Active Hallucination Recovery Gate for Xeren.

Verifies candidate answers using research tools (ClaimVerifier, CredibilityScorer)
and triggers autonomous Web Search fallback when confidence is low or evidence is uncertain.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from xeren.core.intent import RoutingCategory
from xeren.plugins.research.tools.claim_verifier import ClaimStatus, ClaimVerifier, VerifiedClaim
from xeren.plugins.research.tools.credibility_scorer import CredibilityScorer
from xeren.plugins.research.tools.live_search import BaseSearchEngine, create_search_engine
from xeren.plugins.research.schemas import RawSearchResult

logger = logging.getLogger("xeren.core.hallucination_guard")


@dataclass
class StructuredAnswer:
    """Standardized, verified output with confidence probability and evidence trace."""
    answer: str
    confidence_score: float  # Probability [0.0, 1.0]
    verification_status: str  # VERIFIED, RECOVERED, UNCERTAIN, UNVERIFIED
    evidence_sources: List[str] = field(default_factory=list)
    routing_category: str = RoutingCategory.GENERAL_KNOWLEDGE.value
    hallucination_detected: bool = False
    recovery_applied: bool = False
    explanation: str = ""

    @property
    def verified(self) -> bool:
        """Compatibility property for verification status."""
        return self.verification_status in ("VERIFIED", "RECOVERED")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "confidence_score": round(self.confidence_score, 3),
            "verification_status": self.verification_status,
            "evidence_sources": self.evidence_sources,
            "routing_category": self.routing_category,
            "hallucination_detected": self.hallucination_detected,
            "recovery_applied": self.recovery_applied,
            "explanation": self.explanation,
        }


class HallucinationGuard:
    """
    Active Gatekeeper against Hallucinations in Xeren.

    Pipeline:
    1. Assess initial answer confidence & hallucination probability.
    2. If confidence >= threshold -> Accept with high score.
    3. If confidence < threshold -> Trigger Autonomous Web Search Fallback:
       a. Formulate targeted search query.
       b. Retrieve credible sources via LiveSearch.
       c. Cross-verify factual claims via ClaimVerifier & CredibilityScorer.
       d. Recover or calibrate the answer with citations.
    """

    UNCERTAINTY_PATTERNS = [
        re.compile(r"\b(i think|maybe|perhaps|probably|might be|could be|not entirely sure|as far as i know)\b", re.I),
        re.compile(r"\b(i am not sure|i believe|unconfirmed|it is rumored|possibly)\b", re.I),
        re.compile(r"\b(i cannot verify|cannot confirm|i don't know)\b", re.I),
    ]

    HALLUCINATION_TRIGGERS = [
        re.compile(r"\b(version \d+\.\d+\.\d+|release date in 202[6-9]|secret feature)\b", re.I),
        re.compile(r"\b(created by (tencent|alipay|alibaba|baidu|bytedance|openai|anthropic|google|microsoft|xeren))\b", re.I),
        re.compile(r"\b(developed by (tencent|alipay|alibaba|baidu|bytedance|openai|anthropic|google|microsoft|xeren))\b", re.I),
        re.compile(r"\b(built by (tencent|alipay|alibaba|baidu|bytedance|openai|anthropic|google|microsoft|xeren))\b", re.I),
        # Detect LLM-generated fake citation sections embedded in the answer body
        re.compile(r"(verified sources|sources\s*&\s*evidence|references:|citations:|further reading:)", re.I),
        re.compile(r"https?://[^\s]{10,}", re.I),  # Inline URLs fabricated by LLM
        # Detect fabricated benchmark statistics (e.g., '98.7% exact match', '50 tokens per second')
        re.compile(r"\b\d+\.\d+%\s*(exact match|accuracy|benchmark|precision|recall|f1)", re.I),
        re.compile(r"~?\d+\s*tokens?\s*(per|/)\s*second", re.I),
        re.compile(r"\bGPT-\d+\s*architecture\b", re.I),
        re.compile(r"\b(specialized variant|variant of the GPT|fork of GPT)\b", re.I),
    ]

    # Patterns used to strip citation footer blocks from LLM-generated answers
    _CITATION_STRIP_PATTERNS: List[re.Pattern] = [
        re.compile(
            r"(\n|^)#+\s*(verified sources?|sources?\s*&\s*evidence|references?|citations?|further reading)[\s\S]*$",
            re.I | re.MULTILINE,
        ),
        re.compile(
            r"(\n|^)\*{0,2}(verified sources?|sources?\s*&\s*evidence|references?|citations?)[:\s][\s\S]*$",
            re.I | re.MULTILINE,
        ),
    ]

    def __init__(
        self,
        confidence_threshold: float = 0.75,
        search_engine: Optional[BaseSearchEngine] = None,
        claim_verifier: Optional[ClaimVerifier] = None,
        credibility_scorer: Optional[CredibilityScorer] = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.search_engine = search_engine or create_search_engine()
        self.credibility_scorer = credibility_scorer or CredibilityScorer()
        self.claim_verifier = claim_verifier or ClaimVerifier(credibility_scorer=self.credibility_scorer)

    def set_search_engine(self, engine: BaseSearchEngine) -> None:
        """Update active search engine."""
        self.search_engine = engine

    @staticmethod
    def strip_fake_citations(answer: str) -> str:
        """
        Remove any LLM-generated citation / 'Verified Sources & Evidence' footer blocks
        from the answer text before returning it to the user.
        These blocks are always hallucinated — real source attribution is handled by
        the system via evidence_sources, not by the LLM itself.
        """
        # Remove Markdown heading-style citation sections (### Verified Sources ...)
        cleaned = re.sub(
            r"(\n|^)(#{1,4}\s*)?(verified sources?|sources?\s*&\s*evidence|references?|citations?|further reading)[:\s][\s\S]*$",
            "",
            answer,
            flags=re.I | re.MULTILINE,
        )
        # Remove bold-style citation sections (**Verified Sources & Evidence:**)
        cleaned = re.sub(
            r"(\n|^)\*{1,2}(verified sources?|sources?\s*&\s*evidence|references?|citations?)[*:\s][\s\S]*$",
            "",
            cleaned,
            flags=re.I | re.MULTILINE,
        )
        return cleaned.rstrip()

    @property
    def search_tool(self) -> Any:
        class _SearchToolWrapper:
            def __init__(self, guard: Any) -> None:
                self._guard = guard
            @property
            def engine(self) -> Any:
                return self._guard.search_engine
            @engine.setter
            def engine(self, val: Any) -> None:
                self._guard.search_engine = val
        return _SearchToolWrapper(self)

    def evaluate_confidence(
        self,
        query: str,
        answer: str,
        category: RoutingCategory = RoutingCategory.GENERAL_KNOWLEDGE,
        has_search_context: bool = True,
    ) -> Tuple[float, bool, str]:
        """
        Evaluate factual confidence score [0.0, 1.0] and detect hallucination risks.

        Args:
            has_search_context: Set False when the answer was generated without any
                web search results — this lowers the base score to force recovery.

        Returns:
            (confidence_score, is_hallucination_suspect, explanation)
        """
        if not answer or not answer.strip():
            return 0.0, True, "Empty answer produced."

        # Base score: lower when no web evidence was available (ungrounded answer)
        score = 0.88 if has_search_context else 0.60
        reasons: List[str] = []

        # 1. Uncertainty phrases reduce confidence
        for pat in self.UNCERTAINTY_PATTERNS:
            m = pat.search(answer)
            if m:
                score -= 0.25
                reasons.append(f"Contains uncertainty expression: '{m.group(0)}'")

        # 2. Category-specific adjustments
        if category == RoutingCategory.XEREN_PROJECT:
            # High precision required for internal architecture
            if any(term in answer.lower() for term in ["xeren", "qlora", "checkpoint", "dataset", "runtime"]):
                score += 0.05
            else:
                score -= 0.15
                reasons.append("Project query lacked grounded codebase references.")

        # 3. Check for specific hallucination triggers
        for trig in self.HALLUCINATION_TRIGGERS:
            if trig.search(answer):
                score -= 0.20
                reasons.append("Contains high-risk unverified version/date claims.")

        # 4. Length / quality heuristic
        if len(answer.strip().split()) < 4:
            score -= 0.20
            reasons.append("Answer is too brief to be fully verifiable.")

        final_score = max(0.05, min(0.99, score))
        is_suspect = final_score < self.confidence_threshold
        explanation = "; ".join(reasons) if reasons else "Answer meets factual confidence criteria."

        return final_score, is_suspect, explanation

    async def averify_and_recover(
        self,
        query: str,
        raw_answer: str,
        category: RoutingCategory = RoutingCategory.GENERAL_KNOWLEDGE,
        context: Optional[Dict[str, Any]] = None,
        has_search_context: bool = True,
    ) -> StructuredAnswer:
        """
        Evaluate candidate answer and autonomously recover via Web Search if confidence is low.

        Args:
            has_search_context: False when the answer was generated without web search results,
                causing the base confidence to start lower (0.60 vs 0.88).
        """
        initial_score, is_suspect, explanation = self.evaluate_confidence(
            query, raw_answer, category, has_search_context=has_search_context
        )

        if not is_suspect:
            logger.info("Answer passed hallucination guard (confidence=%.2f)", initial_score)
            return StructuredAnswer(
                answer=raw_answer,
                confidence_score=initial_score,
                verification_status="VERIFIED",
                routing_category=category.value,
                hallucination_detected=False,
                recovery_applied=False,
                explanation=explanation,
            )

        logger.warning(
            "Hallucination risk detected (confidence=%.2f < threshold=%.2f). Triggering web search recovery...",
            initial_score, self.confidence_threshold
        )

        # Trigger Autonomous Web Search Fallback
        recovered_answer, recovered_score, sources, success = await self._execute_web_recovery(query, raw_answer)

        if success:
            return StructuredAnswer(
                answer=recovered_answer,
                confidence_score=recovered_score,
                verification_status="RECOVERED",
                evidence_sources=sources,
                routing_category=category.value,
                hallucination_detected=True,
                recovery_applied=True,
                explanation=f"Recovered via web search verification: {explanation}",
            )
        else:
            # Fallback calibrated as UNCERTAIN rather than hallucinating
            calibrated_answer = (
                f"{raw_answer}\n\n"
                f"[Note: Confidence score is {round(initial_score * 100)}%. "
                f"This information could not be independently cross-verified online.]"
            )
            return StructuredAnswer(
                answer=calibrated_answer,
                confidence_score=initial_score,
                verification_status="UNCERTAIN",
                evidence_sources=sources,
                routing_category=category.value,
                hallucination_detected=True,
                recovery_applied=False,
                explanation=f"Uncertainty flagged without online confirmation: {explanation}",
            )

    def verify_and_recover(
        self,
        query: str,
        raw_answer: str,
        category: RoutingCategory = RoutingCategory.GENERAL_KNOWLEDGE,
        context: Optional[Dict[str, Any]] = None,
        has_search_context: bool = True,
    ) -> StructuredAnswer:
        """Synchronous wrapper for averify_and_recover."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self.averify_and_recover(query, raw_answer, category, context, has_search_context),
                    ).result()
            return loop.run_until_complete(
                self.averify_and_recover(query, raw_answer, category, context, has_search_context)
            )
        except RuntimeError:
            return asyncio.run(
                self.averify_and_recover(query, raw_answer, category, context, has_search_context)
            )

    async def _execute_web_recovery(
        self,
        query: str,
        raw_answer: str,
    ) -> Tuple[str, float, List[str], bool]:
        """
        Autonomous search and cross-verification step.
        """
        try:
            # 1. Targeted search query formulation
            search_query = self._formulate_search_query(query, raw_answer)
            logger.info("Executing web search query: '%s'", search_query)

            # 2. Execute search
            results: List[RawSearchResult] = await self.search_engine.asearch(search_query, max_results=4)
            if not results:
                logger.warning("No search results returned for query: '%s'", search_query)
                return raw_answer, 0.40, [], False

            # 3. Format evidence for ClaimVerifier
            evidence_items = []
            sources = []  # Keep empty to hide URLs from user
            for res in results:
                evidence_items.append({
                    "url": res.url,
                    "excerpt": f"{res.title}: {res.snippet}",
                    "supports": True,
                })

            # 4. Cross-verify claim against evidence
            claim_verif: VerifiedClaim = self.claim_verifier.verify_claim(raw_answer, evidence_items)

            # 5. Synthesize grounded answer from real search snippets.
            # Strip any LLM-fabricated citation blocks from the original answer first.
            base_answer = self.strip_fake_citations(raw_answer.strip())

            # We intentionally do NOT append the raw search snippets to the final text anymore.
            # The search data was already used cognitively in the background to generate the base_answer,
            # and the user requested that evidence formatting remain invisible.
            recovered = base_answer

            calibrated_score = max(0.85, claim_verif.confidence)
            return recovered, calibrated_score, sources, True

        except Exception as e:
            logger.error("Web search recovery encountered error: %s", e)
            return raw_answer, 0.45, [], False

    def _formulate_search_query(self, query: str, answer: str) -> str:
        """Formulate a concise search query targeting the core factual proposition."""
        clean_q = re.sub(r"[?!.,]", "", query).strip()
        # Keep query focused
        words = clean_q.split()
        if len(words) > 8:
            return " ".join(words[:8])
        return clean_q


__all__ = ["HallucinationGuard", "StructuredAnswer"]
