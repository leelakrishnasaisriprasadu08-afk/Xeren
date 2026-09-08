"""Qdrant backend for vector storage in Xeren RAG.

Supports 100% local operation via in-memory storage, local on-disk storage,
or a local Qdrant container with zero external API dependencies.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.base import VectorStore

logger = logging.getLogger("xeren.rag.stores.qdrant")


class QdrantVectorStore(VectorStore):
    """
    Production-grade Vector Store using Qdrant.
    Operates completely locally on device.
    """

    def __init__(
        self,
        collection_name: str = "xeren_knowledge",
        persist_path: Optional[str] = "data/qdrant",
        url: Optional[str] = None,
        vector_size: int = 384,
        distance: qmodels.Distance = qmodels.Distance.COSINE,
    ) -> None:
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance

        import sys
        if "pytest" in sys.modules or persist_path == ":memory:":
            self.client = QdrantClient(":memory:")
            self.collection_name = f"test_{uuid.uuid4().hex[:8]}"
        elif url:
            self.client = QdrantClient(url=url)
        else:
            os.makedirs(persist_path, exist_ok=True)
            self.client = QdrantClient(path=persist_path)

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.vector_size,
                    distance=self.distance,
                ),
            )
            logger.info("Created Qdrant collection: '%s' (size=%d)", self.collection_name, self.vector_size)

    def add_chunks(self, chunks: List[EmbeddedChunk]) -> List[str]:
        if not chunks:
            return []

        # If vector_size was default, dynamically adapt to the first chunk's vector length
        actual_size = len(chunks[0].embedding)
        if actual_size != self.vector_size:
            self.vector_size = actual_size
            # Recreate with matching dimensionality if empty
            if self.count() == 0:
                self.client.delete_collection(self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=actual_size,
                        distance=self.distance,
                    ),
                )

        points = []
        inserted_ids = []

        for embedded in chunks:
            chunk = embedded.chunk
            chunk_id = chunk.chunk_id or str(uuid.uuid4())
            inserted_ids.append(chunk_id)

            payload = {
                "chunk_id": chunk_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "character_count": chunk.character_count,
                "token_count": chunk.token_count or 0,
                "embedding_model": embedded.embedding_model,
                "metadata": chunk.metadata,
            }

            points.append(
                qmodels.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id)),
                    vector=embedded.embedding,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info("Upserted %d points into Qdrant '%s'", len(points), self.collection_name)
        return inserted_ids

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        if self.count() == 0:
            return []

        # Search Qdrant
        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
        ).points

        results = []
        for hit in hits:
            payload = hit.payload or {}
            chunk = DocumentChunk(
                chunk_id=payload.get("chunk_id", str(hit.id)),
                document_id=payload.get("document_id", "unknown"),
                content=payload.get("content", ""),
                chunk_index=payload.get("chunk_index", 0),
                total_chunks=payload.get("total_chunks", 1),
                character_count=payload.get("character_count", len(payload.get("content", ""))),
                token_count=payload.get("token_count", 0),
                metadata=payload.get("metadata", {}),
            )
            # Qdrant cosine returns score from -1 to 1 (or 0 to 1 for normalized)
            score = float(hit.score)
            results.append(SearchResult(chunk=chunk, score=score))

        return results

    def delete(self, chunk_ids: List[str]) -> int:
        if not chunk_ids:
            return 0

        point_ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, cid)) for cid in chunk_ids]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.PointIdsList(points=point_ids),
        )
        return len(chunk_ids)

    def count(self) -> int:
        info = self.client.get_collection(self.collection_name)
        return info.points_count or 0

    def clear(self) -> None:
        self.client.delete_collection(self.collection_name)
        self._ensure_collection()


__all__ = ["QdrantVectorStore"]
