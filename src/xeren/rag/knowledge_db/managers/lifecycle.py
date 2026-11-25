"""LifecycleManager enforcing knowledge evolution state transitions in SQLite."""

import time
from typing import Optional, Set
from xeren.rag.knowledge_db.schema.enums import KnowledgeLifecycleState
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class LifecycleManager:
    """Manages legal lifecycle state transitions and non-destructive supersession."""

    # Explicit allowed transition graph
    VALID_TRANSITIONS = {
        KnowledgeLifecycleState.INGESTED: {KnowledgeLifecycleState.PROCESSED, KnowledgeLifecycleState.ARCHIVED},
        KnowledgeLifecycleState.PROCESSED: {KnowledgeLifecycleState.INDEXED, KnowledgeLifecycleState.ARCHIVED},
        KnowledgeLifecycleState.INDEXED: {KnowledgeLifecycleState.VALIDATED, KnowledgeLifecycleState.ARCHIVED},
        KnowledgeLifecycleState.VALIDATED: {KnowledgeLifecycleState.ACTIVE, KnowledgeLifecycleState.ARCHIVED},
        KnowledgeLifecycleState.ACTIVE: {
            KnowledgeLifecycleState.UPDATED,
            KnowledgeLifecycleState.QUALIFIED,
            KnowledgeLifecycleState.CONTRADICTED,
            KnowledgeLifecycleState.SUPERSEDED,
            KnowledgeLifecycleState.ARCHIVED,
        },
        KnowledgeLifecycleState.UPDATED: {
            KnowledgeLifecycleState.ACTIVE,
            KnowledgeLifecycleState.SUPERSEDED,
            KnowledgeLifecycleState.ARCHIVED,
        },
        KnowledgeLifecycleState.QUALIFIED: {
            KnowledgeLifecycleState.ACTIVE,
            KnowledgeLifecycleState.CONTRADICTED,
            KnowledgeLifecycleState.SUPERSEDED,
            KnowledgeLifecycleState.ARCHIVED,
        },
        KnowledgeLifecycleState.CONTRADICTED: {
            KnowledgeLifecycleState.ACTIVE,
            KnowledgeLifecycleState.SUPERSEDED,
            KnowledgeLifecycleState.ARCHIVED,
        },
        KnowledgeLifecycleState.SUPERSEDED: {KnowledgeLifecycleState.ARCHIVED},
        KnowledgeLifecycleState.ARCHIVED: set(),  # Terminal state
    }

    def __init__(self, connection_mgr: ConnectionManager) -> None:
        self.conn_mgr = connection_mgr

    def transition_state(
        self,
        document_id: str,
        target_state: KnowledgeLifecycleState,
        reason: Optional[str] = None,
    ) -> bool:
        """Safely transition document lifecycle state enforcing state machine rules."""
        with self.conn_mgr.transaction() as conn:
            cursor = conn.execute(
                "SELECT lifecycle_state FROM documents WHERE document_id = ?;",
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Document {document_id} not found.")

            current_state = KnowledgeLifecycleState(row["lifecycle_state"])
            allowed = self.VALID_TRANSITIONS.get(current_state, set())

            if target_state not in allowed:
                raise ValueError(
                    f"Illegal lifecycle transition: {current_state.value} -> {target_state.value}. Allowed: {[s.value for s in allowed]}"
                )

            conn.execute(
                "UPDATE documents SET lifecycle_state = ?, updated_at = ? WHERE document_id = ?;",
                (target_state.value, time.time(), document_id),
            )
            return True

    def supersede_document(self, old_document_id: str, new_document_id: str) -> None:
        """Mark an old document SUPERSEDED by a newer authoritative document without deleting history."""
        with self.conn_mgr.transaction() as conn:
            conn.execute(
                """
                UPDATE documents
                SET lifecycle_state = ?, superseded_by_doc_id = ?, updated_at = ?
                WHERE document_id = ?;
                """,
                (
                    KnowledgeLifecycleState.SUPERSEDED.value,
                    new_document_id,
                    time.time(),
                    old_document_id,
                ),
            )
