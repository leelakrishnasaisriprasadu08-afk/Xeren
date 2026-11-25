"""Adapter integrating XerenPatternDB as a first-class VectorStore in Xeren RAG."""

from typing import Dict, List, Optional
import threading

from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.base import VectorStore
from xeren.rag.stores.pattern_db.engine import XerenPatternDB
from xeren.rag.stores.pattern_db.schema import PatternType


class PatternVectorStore(VectorStore):
    """VectorStore implementation powered by Xeren Sovereign Pattern DB."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        auto_persist: bool = False,
        pattern_db: Optional[XerenPatternDB] = None,
    ) -> None:
        self.pattern_db = pattern_db or XerenPatternDB(
            storage_dir=storage_dir, auto_persist=auto_persist
        )
        self._lock = threading.RLock()
        # Keep track of reconstructed DocumentChunks: chunk_id -> DocumentChunk
        self._chunk_registry: Dict[str, DocumentChunk] = {}
        self._rebuild_chunk_registry()

    def _rebuild_chunk_registry(self) -> None:
        """Reconstruct chunk registry from pattern database records."""
        with self._lock:
            self._chunk_registry.clear()
            for rec in self.pattern_db._indexer.records.values():
                if rec.chunk_id not in self._chunk_registry and "text" in rec.payload:
                    meta = rec.payload.get("metadata", {})
                    chunk = DocumentChunk(
                        chunk_id=rec.chunk_id,
                        document_id=rec.document_id,
                        content=rec.payload["text"],
                        chunk_index=rec.features.get("chunk_index", 0),
                        metadata=meta,
                    )
                    self._chunk_registry[rec.chunk_id] = chunk

    def add_chunks(self, chunks: List[EmbeddedChunk]) -> List[str]:
        """Insert embedded chunks into the pattern database."""
        with self._lock:
            inserted_ids: List[str] = []
            for item in chunks:
                chunk = item.chunk
                vector = item.embedding
                self.pattern_db.ingest_chunk_patterns(chunk, vector=vector)
                self._chunk_registry[chunk.chunk_id] = chunk
                inserted_ids.append(chunk.chunk_id)
            return inserted_ids

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Perform dense semantic similarity search over pattern records."""
        with self._lock:
            dense_hits = self.pattern_db._indexer.search_dense(
                query_vector=query_vector,
                top_k=top_k * 3,  # Candidate pool for metadata filter evaluation
            )

            results: List[SearchResult] = []
            seen_chunks = set()

            for rec, score in dense_hits:
                if rec.chunk_id in seen_chunks:
                    continue

                chunk = self._chunk_registry.get(rec.chunk_id)
                if not chunk:
                    continue

                # Apply metadata filter if supplied
                if filter and not filter.matches(chunk.metadata):
                    continue

                seen_chunks.add(rec.chunk_id)
                results.append(
                    SearchResult(
                        chunk=chunk,
                        score=score,
                        retrieval_type="dense",
                        vector=rec.vector,
                    )
                )

                if len(results) >= top_k:
                    break

            return results

    def delete(self, chunk_ids: List[str]) -> int:
        """Delete chunks and all their associated multi-patterns."""
        with self._lock:
            deleted_chunks = 0
            for cid in chunk_ids:
                if cid in self._chunk_registry:
                    del self._chunk_registry[cid]
                    self.pattern_db.delete_chunk(cid)
                    deleted_chunks += 1
            return deleted_chunks

    def count(self) -> int:
        """Return number of distinct document chunks stored."""
        with self._lock:
            return len(self._chunk_registry)

    def clear(self) -> None:
        """Wipe all chunks and patterns from the store."""
        with self._lock:
            self._chunk_registry.clear()
            self.pattern_db.clear()
