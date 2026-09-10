"""Qdrant backend for vector storage in Xeren RAG.

Supports 100% local operation via in-memory storage, local on-disk storage,
or a local Qdrant container with zero external API dependencies.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError:
    QdrantClient = None
    qmodels = None

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
        api_key: Optional[str] = None,
        vector_size: int = 384,
        distance: Optional[Any] = None,
    ) -> None:
        if QdrantClient is None or qmodels is None:
            raise ImportError(
                "qdrant-client is required for QdrantVectorStore. Install it with: pip install qdrant-client"
            )
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance or qmodels.Distance.COSINE

        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        target_url = url or os.getenv("QDRANT_URL")
        target_api_key = api_key or os.getenv("QDRANT_API_KEY")

        import sys
        if "pytest" in sys.modules or persist_path == ":memory:":
            self.client = QdrantClient(":memory:")
            self.collection_name = f"test_{uuid.uuid4().hex[:8]}"
        elif target_url:
            self.client = QdrantClient(url=target_url, api_key=target_api_key)
        else:
            effective_path = persist_path or os.getenv("QDRANT_PATH", "data/qdrant")
            os.makedirs(effective_path, exist_ok=True)
            self.client = QdrantClient(path=effective_path)

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
                "metadata": chunk.metadata or {},
            }
            # Elevate authorization & tenant fields to top-level payload for fast index filtering
            for auth_field in ("tenant_id", "owner_id", "access_level", "department"):
                if auth_field in chunk.metadata:
                    payload[auth_field] = chunk.metadata[auth_field]

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

    def _build_qdrant_filter(self, filter: Optional[MetadataFilter]) -> Optional[qmodels.Filter]:
        """Translate a Xeren MetadataFilter into a native Qdrant query filter."""
        if not filter or not filter.conditions:
            return None

        from xeren.rag.retrieval.filter import FilterOperator

        conditions: List[Any] = []
        for cond in filter.conditions:
            key = cond.field
            if cond.operator == FilterOperator.EQ:
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=cond.value),
                    )
                )
            elif cond.operator == FilterOperator.IN:
                val_list = list(cond.value) if isinstance(cond.value, (list, set, tuple)) else [cond.value]
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchAny(any=val_list),
                    )
                )
            elif cond.operator == FilterOperator.NEQ:
                conditions.append(
                    qmodels.Filter(
                        must_not=[
                            qmodels.FieldCondition(
                                key=key,
                                match=qmodels.MatchValue(value=cond.value),
                            )
                        ]
                    )
                )

        if not conditions:
            return None

        if filter.logic == "OR":
            return qmodels.Filter(should=conditions)
        return qmodels.Filter(must=conditions)

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        if self.count() == 0:
            return []

        # Build native index-level authorization filter
        query_filter = self._build_qdrant_filter(filter)

        # Search Qdrant with pre-retrieval filter enforced
        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
        ).points

        results = []
        for hit in hits:
            payload = hit.payload or {}
            meta = dict(payload.get("metadata", {}))
            # Restore elevated authorization fields into metadata
            for auth_field in ("tenant_id", "owner_id", "access_level", "department"):
                if auth_field in payload and auth_field not in meta:
                    meta[auth_field] = payload[auth_field]

            chunk = DocumentChunk(
                chunk_id=payload.get("chunk_id", str(hit.id)),
                document_id=payload.get("document_id", "unknown"),
                content=payload.get("content", ""),
                chunk_index=payload.get("chunk_index", 0),
                total_chunks=payload.get("total_chunks", 1),
                character_count=payload.get("character_count", len(payload.get("content", ""))),
                token_count=payload.get("token_count", 0),
                metadata=meta,
            )
            # Qdrant cosine returns score from -1 to 1 (or 0 to 1 for normalized)
            score = hit.score
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
