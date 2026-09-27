"""Abstract base interface for RAG rerankers."""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional

from xeren.rag.retrieval.types import SearchResult


class BaseReranker(ABC):
    """Abstract base class for all RAG rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        """Rerank and filter search results for a given query."""
        pass

    async def arerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        """Asynchronously rerank search results."""
        return await asyncio.to_thread(self.rerank, query, results, top_n)
