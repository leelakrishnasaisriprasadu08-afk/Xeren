"""Score threshold filtering and composite rerankers."""

from typing import List, Optional

from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.types import SearchResult


class ScoreThresholdReranker(BaseReranker):
    """Filters out search results falling below a minimum confidence score."""

    def __init__(self, min_score: float = 0.5) -> None:
        self.min_score = min_score

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        filtered = [r for r in results if r.score >= self.min_score]
        filtered.sort(key=lambda x: x.score, reverse=True)
        if top_n is not None:
            return filtered[:top_n]
        return filtered


class CompositeReranker(BaseReranker):
    """Executes multiple rerankers in sequential pipeline order."""

    def __init__(self, rerankers: List[BaseReranker]) -> None:
        self.rerankers = rerankers

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        current_results = results
        for reranker in self.rerankers:
            current_results = reranker.rerank(query, current_results)

        if top_n is not None:
            return current_results[:top_n]
        return current_results
