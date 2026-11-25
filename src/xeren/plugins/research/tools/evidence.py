"""Evidence extraction tool extracting atomic factual claims and citations from ranked sources."""

import re
from typing import Any, List, Optional

from xeren.models.base import BaseLLM
from xeren.models.types import ChatMessage
from xeren.plugins.research.schemas import EvidenceItem, RankedSource
from xeren.plugins.research.tools.base import BaseResearchTool


class EvidenceExtractionTool(BaseResearchTool):
    """Extracts verifiable atomic evidence items and citations from ranked sources."""

    def __init__(self, llm: Optional[BaseLLM] = None) -> None:
        self.llm = llm

    @property
    def name(self) -> str:
        return "evidence_extraction"

    @property
    def description(self) -> str:
        return "Extracts atomic factual claims, empirical data points, and provenance citations from sources."

    def _extract_sentences(self, text: str) -> List[str]:
        """Split text into informative sentences."""
        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in raw_sentences if len(s.strip()) > 20]

    def execute(
        self,
        objective: str,
        sources: List[RankedSource],
        max_evidence_per_source: int = 3,
        **kwargs: Any,
    ) -> List[EvidenceItem]:
        """Extract atomic evidence items with citation markers from selected sources."""
        evidence_items: List[EvidenceItem] = []
        ev_counter = 1

        selected_sources = [s for s in sources if s.selected]
        for src_idx, source in enumerate(selected_sources):
            citation_marker = f"[{src_idx + 1}]"
            sentences = self._extract_sentences(source.snippet)
            if not sentences:
                sentences = [source.snippet.strip()]

            for sent in sentences[:max_evidence_per_source]:
                item = EvidenceItem(
                    evidence_id=f"ev-{ev_counter}",
                    fact_statement=sent,
                    source_id=source.source_id,
                    source_url=source.url,
                    confidence=round(min(1.0, max(0.5, source.relevance_score)), 2),
                    citation_marker=citation_marker,
                    context_passage=source.snippet,
                )
                evidence_items.append(item)
                ev_counter += 1

        return evidence_items


__all__ = ["EvidenceExtractionTool"]
