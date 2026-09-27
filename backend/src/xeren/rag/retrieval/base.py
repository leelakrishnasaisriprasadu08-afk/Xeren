"""Abstract base retriever interface for Xeren RAG."""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional

from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult


class BaseRetriever(ABC):
    """Abstract base class for all RAG retrieval strategies."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Retrieve relevant document chunks for a query string."""
        pass

    async def aretrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Asynchronously retrieve relevant document chunks for a query string."""
        return await asyncio.to_thread(self.retrieve, query, top_k, filter)
