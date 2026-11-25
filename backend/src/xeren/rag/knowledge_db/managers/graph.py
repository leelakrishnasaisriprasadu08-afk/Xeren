"""GraphManager handling semantic relationships and knowledge graph traversals in SQLite."""

from typing import List, Optional
from xeren.rag.knowledge_db.schema.enums import KnowledgeRelationshipType
from xeren.rag.knowledge_db.schema.models import KnowledgeRelationshipRecord
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class GraphManager:
    """Manages knowledge_relationships graph edges and traversal queries in SQLite."""

    def __init__(self, connection_mgr: ConnectionManager) -> None:
        self.conn_mgr = connection_mgr

    def add_relationship(
        self,
        source_chunk_id: str,
        target_chunk_id: str,
        relationship_type: KnowledgeRelationshipType,
        confidence: float = 1.0,
        evidence_reference: Optional[str] = None,
        model_id: str = "xeren_ingest",
        created_by: str = "system",
        status: str = "ACTIVE",
    ) -> KnowledgeRelationshipRecord:
        """Create and store a semantic knowledge graph edge."""
        rel = KnowledgeRelationshipRecord(
            source_chunk_id=source_chunk_id,
            target_chunk_id=target_chunk_id,
            relationship_type=relationship_type,
            confidence=confidence,
            evidence_reference=evidence_reference,
            model_id=model_id,
            created_by=created_by,
            status=status,
        )

        with self.conn_mgr.transaction() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_relationships (
                    relationship_id, source_chunk_id, relationship_type,
                    target_chunk_id, confidence, evidence_reference,
                    model_id, created_by, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    rel.relationship_id,
                    rel.source_chunk_id,
                    rel.relationship_type.value,
                    rel.target_chunk_id,
                    rel.confidence,
                    rel.evidence_reference,
                    rel.model_id,
                    rel.created_by,
                    rel.status,
                    rel.created_at,
                ),
            )
        return rel

    def get_relationships(
        self,
        chunk_id: str,
        direction: str = "both",
        relationship_type: Optional[KnowledgeRelationshipType] = None,
    ) -> List[KnowledgeRelationshipRecord]:
        """Fetch relations connected to a chunk."""
        conn = self.conn_mgr.get_connection()
        clauses = []
        params = []

        if direction == "outgoing":
            clauses.append("source_chunk_id = ?")
            params.append(chunk_id)
        elif direction == "incoming":
            clauses.append("target_chunk_id = ?")
            params.append(chunk_id)
        else:
            clauses.append("(source_chunk_id = ? OR target_chunk_id = ?)")
            params.extend([chunk_id, chunk_id])

        if relationship_type:
            clauses.append("relationship_type = ?")
            params.append(relationship_type.value)

        sql = f"SELECT * FROM knowledge_relationships WHERE {' AND '.join(clauses)} AND status = 'ACTIVE';"
        cursor = conn.execute(sql, tuple(params))

        results: List[KnowledgeRelationshipRecord] = []
        for row in cursor.fetchall():
            results.append(
                KnowledgeRelationshipRecord(
                    relationship_id=row["relationship_id"],
                    source_chunk_id=row["source_chunk_id"],
                    relationship_type=KnowledgeRelationshipType(row["relationship_type"]),
                    target_chunk_id=row["target_chunk_id"],
                    confidence=row["confidence"],
                    evidence_reference=row["evidence_reference"],
                    model_id=row["model_id"],
                    created_by=row["created_by"],
                    status=row["status"],
                    created_at=row["created_at"],
                )
            )
        return results

    def find_contradictions(self, chunk_id: str) -> List[KnowledgeRelationshipRecord]:
        """Find any chunks that actively contradict or are contradicted by this chunk."""
        return self.get_relationships(
            chunk_id=chunk_id,
            relationship_type=KnowledgeRelationshipType.CONTRADICTS,
        )

    def find_supporting_evidence(self, chunk_id: str) -> List[KnowledgeRelationshipRecord]:
        """Find chunks that provide evidentiary support for this chunk."""
        return self.get_relationships(
            chunk_id=chunk_id,
            direction="outgoing",
            relationship_type=KnowledgeRelationshipType.SUPPORTS,
        )

    def count_relationships(self) -> int:
        """Count total registered knowledge edges."""
        conn = self.conn_mgr.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM knowledge_relationships;")
        row = cursor.fetchone()
        return row[0] if row else 0
