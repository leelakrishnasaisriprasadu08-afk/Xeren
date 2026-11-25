"""VectorStore compatibility adapter for Xeren Sovereign Knowledge DB."""

import threading
from typing import List, Optional

from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.knowledge_db.api import IKnowledgeDB
from xeren.rag.knowledge_db.client import KnowledgeDBClient
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.base import VectorStore


class KnowledgeDBVectorStoreAdapter(VectorStore):
    """Adapter allowing KnowledgeDBClient to serve as a standard VectorStore."""

    def __init__(
        self,
        knowledge_db: Optional[IKnowledgeDB] = None,
        default_model_id: str = "default_embed_model",
    ) -> None:
        self.db = knowledge_db or KnowledgeDBClient()
        self.default_model_id = default_model_id
        self._lock = threading.RLock()

    def add_chunks(self, chunks: List[EmbeddedChunk]) -> List[str]:
        """Ingest embedded chunks into the sovereign knowledge database."""
        with self._lock:
            inserted_ids: List[str] = []
            for item in chunks:
                chunk = item.chunk
                vector = item.embedding
                model_id = item.embedding_model or self.default_model_id

                source_uri = chunk.metadata.get("source") or f"doc://{chunk.document_id}"
                title = chunk.metadata.get("title") or f"Doc {chunk.document_id}"
                workspace_id = chunk.metadata.get("workspace_id", "default")
                access_level = chunk.metadata.get("access_level", "LIBERAL")

                # Ingest document or chunk
                receipt = self.db.ingest_document(
                    source_uri=source_uri,
                    content=chunk.content,
                    title=title,
                    workspace_id=workspace_id,
                    access_level=access_level,
                    embedding_vector=vector,
                    embedding_model_id=model_id,
                    metadata=chunk.metadata,
                )
                inserted_ids.append(chunk.chunk_id)

            return inserted_ids

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Execute similarity search against Knowledge DB."""
        with self._lock:
            result = self.db.retrieve(
                query="",
                query_vector=query_vector,
                model_id=self.default_model_id,
                top_k=top_k,
                filter=filter,
            )

            return [
                SearchResult(
                    chunk=item.chunk,
                    score=item.score,
                    retrieval_type="knowledge_db",
                    vector=query_vector,
                )
                for item in result.items
            ]

    def delete(self, chunk_ids: List[str]) -> int:
        """Delete chunks from Knowledge DB."""
        with self._lock:
            if not isinstance(self.db, KnowledgeDBClient):
                return 0
            with self.db.conn_mgr.transaction() as conn:
                qmarks = ",".join("?" for _ in chunk_ids)
                cursor = conn.execute(f"DELETE FROM chunks WHERE chunk_id IN ({qmarks});", chunk_ids)
                deleted = cursor.rowcount
            self.db.vector_mgr.delete_embeddings(chunk_ids)
            return deleted

    def count(self) -> int:
        """Total chunks stored."""
        with self._lock:
            if not isinstance(self.db, KnowledgeDBClient):
                return 0
            conn = self.db.conn_mgr.get_connection()
            cursor = conn.execute("SELECT COUNT(*) FROM chunks;")
            row = cursor.fetchone()
            return row[0] if row else 0

    def clear(self) -> None:
        """Reset knowledge database."""
        with self._lock:
            if not isinstance(self.db, KnowledgeDBClient):
                return
            with self.db.conn_mgr.transaction() as conn:
                conn.execute("DELETE FROM documents;")
                conn.execute("DELETE FROM sources;")
                conn.execute("DELETE FROM claims;")
            self.db.vector_engine.clear()
