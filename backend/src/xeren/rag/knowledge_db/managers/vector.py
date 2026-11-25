"""VectorIndexManager coordinating SQLite embedding metadata with pluggable vector index."""

import struct
from typing import Dict, List, Optional, Set, Tuple
from xeren.rag.knowledge_db.indexing.base import IVectorIndexEngine
from xeren.rag.knowledge_db.schema.models import EmbeddingRecord
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class VectorIndexManager:
    """Manages decoupled embedding metadata in SQLite and dispatches to IVectorIndexEngine."""

    def __init__(
        self,
        connection_mgr: ConnectionManager,
        vector_engine: IVectorIndexEngine,
    ) -> None:
        self.conn_mgr = connection_mgr
        self.vector_engine = vector_engine

    def record_embedding(
        self,
        chunk_id: str,
        model_id: str,
        vector: List[float],
        store_recovery_blob: bool = True,
        version: int = 1,
    ) -> EmbeddingRecord:
        """Store embedding metadata in SQLite and index into vector engine."""
        dim = len(vector)
        index_id = f"{model_id}:{chunk_id}:v{version}"
        blob = None
        if store_recovery_blob:
            # IEEE 754 32-bit float serialization
            blob = struct.pack(f"<{dim}f", *vector)

        rec = EmbeddingRecord(
            chunk_id=chunk_id,
            model_id=model_id,
            dimension=dim,
            index_id=index_id,
            vector_blob=blob,
            version=version,
        )

        with self.conn_mgr.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings (
                    embedding_id, chunk_id, model_id, dimension, index_id,
                    vector_blob, version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    rec.embedding_id,
                    rec.chunk_id,
                    rec.model_id,
                    rec.dimension,
                    rec.index_id,
                    rec.vector_blob,
                    rec.version,
                    rec.created_at,
                ),
            )

        # Index in active vector engine
        self.vector_engine.index_vectors(
            model_id=model_id,
            dimension=dim,
            vectors={chunk_id: vector},
        )

        return rec

    def search_vectors(
        self,
        model_id: str,
        query_vector: List[float],
        top_k: int = 5,
        candidate_chunk_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Search vector engine using query vector."""
        return self.vector_engine.search_vectors(
            model_id=model_id,
            query_vector=query_vector,
            top_k=top_k,
            candidate_chunk_ids=candidate_chunk_ids,
        )

    def delete_embeddings(self, chunk_ids: List[str], model_id: Optional[str] = None) -> int:
        """Remove embeddings from SQLite and vector engine."""
        if not chunk_ids:
            return 0
        with self.conn_mgr.transaction() as conn:
            if model_id:
                qmarks = ",".join("?" for _ in chunk_ids)
                conn.execute(
                    f"DELETE FROM embeddings WHERE model_id = ? AND chunk_id IN ({qmarks});",
                    [model_id, *chunk_ids],
                )
                self.vector_engine.delete_vectors(model_id, chunk_ids)
            else:
                qmarks = ",".join("?" for _ in chunk_ids)
                conn.execute(
                    f"DELETE FROM embeddings WHERE chunk_id IN ({qmarks});",
                    chunk_ids,
                )
        return len(chunk_ids)

    def count(self, model_id: Optional[str] = None) -> int:
        """Count registered embeddings in SQLite."""
        conn = self.conn_mgr.get_connection()
        if model_id:
            cursor = conn.execute("SELECT COUNT(*) FROM embeddings WHERE model_id = ?;", (model_id,))
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM embeddings;")
        row = cursor.fetchone()
        return row[0] if row else 0
