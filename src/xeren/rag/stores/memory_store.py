"""Thread-safe in-memory vector store with cosine similarity and metadata filtering."""

import math
import threading
from typing import Dict, List, Optional

from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.base import VectorStore


class InMemoryVectorStore(VectorStore):
    """In-memory vector database for fast similarity search and testing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, EmbeddedChunk] = {}

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        if len(vec_a) != len(vec_b) or not vec_a:
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def add_chunks(self, chunks: List[EmbeddedChunk]) -> List[str]:
        with self._lock:
            inserted_ids = []
            for chunk in chunks:
                chunk_id = chunk.chunk.chunk_id
                self._store[chunk_id] = chunk
                inserted_ids.append(chunk_id)
            return inserted_ids

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        with self._lock:
            scored_results: List[SearchResult] = []

            for embedded_chunk in self._store.values():
                # Apply metadata filter
                if filter and not filter.matches(embedded_chunk.chunk.metadata):
                    continue

                score = self._cosine_similarity(query_vector, embedded_chunk.embedding)
                scored_results.append(
                    SearchResult(
                        chunk=embedded_chunk.chunk,
                        score=score,
                        retrieval_type="dense",
                        vector=embedded_chunk.embedding,
                    )
                )

            # Sort by score descending
            scored_results.sort(key=lambda x: x.score, reverse=True)
            return scored_results[:top_k]

    def delete(self, chunk_ids: List[str]) -> int:
        with self._lock:
            count = 0
            for cid in chunk_ids:
                if cid in self._store:
                    del self._store[cid]
                    count += 1
            return count

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def get_all_chunks(self) -> List[EmbeddedChunk]:
        """Return all embedded chunks currently in the store."""
        with self._lock:
            return list(self._store.values())
