"""Mock reranker for deterministic unit testing."""

from typing import Callable, List, Optional

from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.types import SearchResult


class MockReranker(BaseReranker):
    """Deterministic reranker that can re-score chunks or reverse/reorder them for testing."""

    def __init__(
        self,
        score_modifier: Optional[Callable[[str, SearchResult], float]] = None,
        reverse_order: bool = False,
    ) -> None:
        self.score_modifier = score_modifier
        self.reverse_order = reverse_order

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        reranked = []
        for r in results:
            new_score = self.score_modifier(query, r) if self.score_modifier else r.score
            reranked.append(
                SearchResult(
                    chunk=r.chunk,
                    score=new_score,
                    retrieval_type="reranked",
                    vector=r.vector,
                )
            )

        reranked.sort(key=lambda x: x.score, reverse=not self.reverse_order)
        if top_n is not None:
            return reranked[:top_n]
        return reranked
