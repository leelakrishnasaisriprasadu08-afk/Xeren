"""Source ranking and relevance filtering tool reusing Xeren RAG reranker abstractions."""

import re
from typing import Any, Dict, List, Optional

from xeren.plugins.research.schemas import RankedSource, RawSearchResult
from xeren.plugins.research.tools.base import BaseResearchTool
from xeren.rag.document import DocumentChunk
from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.rerankers.threshold import ScoreThresholdReranker
from xeren.rag.retrieval.types import SearchResult


class SourceRankingTool(BaseResearchTool):
    """Ranks, deduplicates, and filters retrieved search results using Xeren RAG reranking abstractions."""

    def __init__(self, reranker: Optional[BaseReranker] = None) -> None:
        self.reranker = reranker

    @property
    def name(self) -> str:
        return "source_ranking"

    @property
    def description(self) -> str:
        return "Ranks candidate search results by relevance to research objective and applies threshold filtering."

    def _compute_relevance(self, query: str, result: RawSearchResult) -> float:
        """Compute base relevance score from query term overlap and search score."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return min(1.0, max(0.0, result.score or 0.5))

        content_tokens = set(re.findall(r"\w+", (result.title + " " + result.snippet).lower()))
        overlap = len(q_tokens & content_tokens)
        jaccard = overlap / len(q_tokens | content_tokens) if (q_tokens | content_tokens) else 0.0
        coverage = overlap / len(q_tokens) if q_tokens else 0.0

        # Weighted combination of search provider score and term coverage
        base_score = result.score if result.score > 0 else 0.5
        combined = 0.4 * base_score + 0.4 * coverage + 0.2 * jaccard
        return round(min(1.0, max(0.0, combined)), 3)

    def execute(
        self,
        objective: str,
        results: List[RawSearchResult],
        max_sources: int = 5,
        min_relevance_score: float = 0.3,
        **kwargs: Any,
    ) -> List[RankedSource]:
        """Rank, deduplicate, and filter search results into RankedSource items."""
        if not results:
            return []

        # 1. Deduplicate by URL
        unique_results: Dict[str, RawSearchResult] = {}
        for r in results:
            clean_url = r.url.strip().lower()
            if clean_url not in unique_results:
                unique_results[clean_url] = r

        # 2. Bridge to Xeren RAG SearchResult & DocumentChunk structures
        rag_results: List[SearchResult] = []
        for idx, r in enumerate(unique_results.values()):
            relevance = self._compute_relevance(objective, r)
            chunk = DocumentChunk(
                chunk_id=f"chunk-{idx + 1}",
                document_id=r.url,
                content=r.snippet,
                chunk_index=0,
                total_chunks=1,
                metadata={
                    "url": r.url,
                    "title": r.title,
                    "author": r.author,
                    "published_date": r.published_date,
                    "full_content": r.full_content,
                },
            )
            rag_results.append(SearchResult(chunk=chunk, score=relevance, retrieval_type="web_search"))

        # 3. Apply Xeren RAG Reranker if configured, else threshold filter
        if self.reranker is not None:
            reranked = self.reranker.rerank(objective, rag_results, top_n=max_sources)
        else:
            # Reuse Xeren RAG ScoreThresholdReranker
            threshold_reranker = ScoreThresholdReranker(min_score=min_relevance_score)
            reranked = threshold_reranker.rerank(objective, rag_results, top_n=max_sources)

        # 4. Map back to RankedSource schemas with source IDs
        ranked_sources: List[RankedSource] = []
        for i, sr in enumerate(reranked):
            meta = sr.chunk.metadata
            ranked_sources.append(
                RankedSource(
                    source_id=f"src-{i + 1}",
                    url=str(meta.get("url", sr.chunk.document_id)),
                    title=str(meta.get("title", f"Source {i + 1}")),
                    snippet=sr.chunk.content,
                    relevance_score=sr.score,
                    selected=sr.score >= min_relevance_score,
                    relevance_rationale=f"Score {sr.score:.2f} based on content relevance to objective.",
                )
            )

        return ranked_sources


__all__ = ["SourceRankingTool"]
