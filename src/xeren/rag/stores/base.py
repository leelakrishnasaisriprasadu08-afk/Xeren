"""Abstract base vector store interface for Xeren RAG."""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional

from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult


class VectorStore(ABC):
    """Abstract base class for vector store implementations."""

    @abstractmethod
    def add_chunks(self, chunks: List[EmbeddedChunk]) -> List[str]:
        """Insert embedded chunks into the vector store. Returns list of inserted chunk IDs."""
        pass

    async def aadd_chunks(self, chunks: List[EmbeddedChunk]) -> List[str]:
        """Asynchronously insert embedded chunks into the vector store."""
        return await asyncio.to_thread(self.add_chunks, chunks)

    @abstractmethod
    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Find the top-k most similar chunks to query_vector, optionally applying a metadata filter."""
        pass

    async def asimilarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Asynchronously find top-k similar chunks."""
        return await asyncio.to_thread(self.similarity_search, query_vector, top_k, filter)

    @abstractmethod
    def delete(self, chunk_ids: List[str]) -> int:
        """Delete chunks by their IDs. Returns count of deleted chunks."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return the total number of stored chunks."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored chunks from the store."""
        pass
