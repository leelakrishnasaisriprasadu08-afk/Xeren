"""RetrievalTelemetryManager handling privacy-controlled retrieval events in SQLite."""

import hashlib
import time
from typing import List, Optional
from xeren.rag.knowledge_db.schema.enums import TelemetryPrivacyPolicy
from xeren.rag.knowledge_db.schema.models import RetrievalEventRecord
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class RetrievalTelemetryManager:
    """Records retrieval events with strict privacy policy controls."""

    def __init__(
        self,
        connection_mgr: ConnectionManager,
        privacy_policy: TelemetryPrivacyPolicy = TelemetryPrivacyPolicy.HASH_ONLY,
    ) -> None:
        self.conn_mgr = connection_mgr
        self.privacy_policy = privacy_policy

    def record_event(
        self,
        query_id: str,
        query_text: str,
        chunk_id: str,
        retrieval_method: str,
        rank_position: int,
        score: float,
        workspace_id: str = "default",
        user_or_task_id: Optional[str] = None,
    ) -> RetrievalEventRecord:
        """Record a single retrieval event adhering to privacy policy."""
        q_norm = query_text.strip().lower()
        q_hash = hashlib.sha256(q_norm.encode("utf-8")).hexdigest()

        # Apply privacy policy
        stored_text: Optional[str] = None
        if self.privacy_policy == TelemetryPrivacyPolicy.FULL:
            stored_text = query_text
        elif self.privacy_policy == TelemetryPrivacyPolicy.MINIMIZED:
            stored_text = query_text[:60] if len(query_text) > 60 else query_text
        elif self.privacy_policy == TelemetryPrivacyPolicy.HASH_ONLY:
            stored_text = None

        event = RetrievalEventRecord(
            query_id=query_id,
            query_hash=q_hash,
            query_text=stored_text,
            chunk_id=chunk_id,
            retrieval_method=retrieval_method,
            rank_position=rank_position,
            score=score,
            workspace_id=workspace_id,
            user_or_task_id=user_or_task_id,
        )

        with self.conn_mgr.transaction() as conn:
            conn.execute(
                """
                INSERT INTO retrieval_events (
                    event_id, query_id, query_hash, query_text, chunk_id,
                    retrieval_method, rank_position, score, user_or_task_id,
                    workspace_id, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.event_id,
                    event.query_id,
                    event.query_hash,
                    event.query_text,
                    event.chunk_id,
                    event.retrieval_method,
                    event.rank_position,
                    event.score,
                    event.user_or_task_id,
                    event.workspace_id,
                    event.timestamp,
                ),
            )
        return event

    def get_events_for_query(self, query_id: str) -> List[RetrievalEventRecord]:
        """Fetch all chunk hits logged for a query ID."""
        conn = self.conn_mgr.get_connection()
        cursor = conn.execute("SELECT * FROM retrieval_events WHERE query_id = ? ORDER BY rank_position ASC;", (query_id,))
        results: List[RetrievalEventRecord] = []
        for row in cursor.fetchall():
            results.append(
                RetrievalEventRecord(
                    event_id=row["event_id"],
                    query_id=row["query_id"],
                    query_hash=row["query_hash"],
                    query_text=row["query_text"],
                    chunk_id=row["chunk_id"],
                    retrieval_method=row["retrieval_method"],
                    rank_position=row["rank_position"],
                    score=row["score"],
                    workspace_id=row["workspace_id"],
                    user_or_task_id=row["user_or_task_id"],
                    timestamp=row["timestamp"],
                )
            )
        return results
