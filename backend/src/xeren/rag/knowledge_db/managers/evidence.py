"""EvidenceManager managing claims, claim_evidence, and provenance traceability in SQLite."""

import time
from typing import Any, Dict, List, Optional
from xeren.rag.knowledge_db.schema.enums import ClaimType
from xeren.rag.knowledge_db.schema.models import (
    ClaimEvidenceRecord,
    ClaimReceipt,
    ClaimRecord,
    ProvenanceRecord,
)
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class EvidenceManager:
    """Manages the verification chain: Claim -> Evidence -> Chunk -> Document -> Source."""

    def __init__(self, connection_mgr: ConnectionManager) -> None:
        self.conn_mgr = connection_mgr

    def record_claim(
        self,
        statement: str,
        supporting_chunk_ids: List[str],
        claim_type: ClaimType = ClaimType.FACT,
        confidence: float = 1.0,
    ) -> ClaimReceipt:
        """Register a claim and link supporting chunk evidence."""
        claim = ClaimRecord(statement=statement, claim_type=claim_type, confidence=confidence)

        with self.conn_mgr.transaction() as conn:
            conn.execute(
                "INSERT INTO claims (claim_id, statement, claim_type, confidence, created_at) VALUES (?, ?, ?, ?, ?);",
                (claim.claim_id, claim.statement, claim.claim_type.value, claim.confidence, claim.created_at),
            )

            evidence_ids = []
            for cid in supporting_chunk_ids:
                ev = ClaimEvidenceRecord(claim_id=claim.claim_id, chunk_id=cid)
                evidence_ids.append(ev.evidence_id)
                conn.execute(
                    """
                    INSERT INTO claim_evidence (
                        evidence_id, claim_id, chunk_id, relevance_score,
                        verification_status, verified_by_model, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        ev.evidence_id,
                        ev.claim_id,
                        ev.chunk_id,
                        ev.relevance_score,
                        ev.verification_status,
                        ev.verified_by_model,
                        ev.created_at,
                    ),
                )

        return ClaimReceipt(
            claim_id=claim.claim_id,
            statement=claim.statement,
            evidence_count=len(supporting_chunk_ids),
            provenance_ids=evidence_ids,
        )

    def record_provenance(
        self,
        chunk_id: str,
        document_id: str,
        source_uri: str,
        document_version: int = 1,
        page_number: Optional[int] = None,
        claim_id: Optional[str] = None,
    ) -> ProvenanceRecord:
        """Record an immutable provenance link."""
        rec = ProvenanceRecord(
            claim_id=claim_id,
            chunk_id=chunk_id,
            document_id=document_id,
            source_uri=source_uri,
            document_version=document_version,
            page_number=page_number,
        )
        with self.conn_mgr.transaction() as conn:
            conn.execute(
                """
                INSERT INTO provenance (
                    provenance_id, claim_id, chunk_id, document_id,
                    source_uri, document_version, page_number, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    rec.provenance_id,
                    rec.claim_id,
                    rec.chunk_id,
                    rec.document_id,
                    rec.source_uri,
                    rec.document_version,
                    rec.page_number,
                    rec.recorded_at,
                ),
            )
        return rec

    def trace_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """Trace a claim back to its supporting evidence chunks, documents, and origin sources."""
        conn = self.conn_mgr.get_connection()
        cursor = conn.execute("SELECT * FROM claims WHERE claim_id = ?;", (claim_id,))
        claim_row = cursor.fetchone()
        if not claim_row:
            return None

        ev_cursor = conn.execute(
            """
            SELECT e.evidence_id, e.relevance_score, e.verification_status,
                   c.chunk_id, c.content, c.document_id,
                   d.title as doc_title, d.source_id, s.source_uri, s.source_type
            FROM claim_evidence e
            JOIN chunks c ON e.chunk_id = c.chunk_id
            JOIN documents d ON c.document_id = d.document_id
            JOIN sources s ON d.source_id = s.source_id
            WHERE e.claim_id = ?;
            """,
            (claim_id,),
        )

        evidence_items = []
        for row in ev_cursor.fetchall():
            evidence_items.append({
                "evidence_id": row["evidence_id"],
                "chunk_id": row["chunk_id"],
                "chunk_content": row["content"],
                "document_id": row["document_id"],
                "document_title": row["doc_title"],
                "source_uri": row["source_uri"],
                "source_type": row["source_type"],
                "relevance_score": row["relevance_score"],
                "verification_status": row["verification_status"],
            })

        return {
            "claim_id": claim_id,
            "statement": claim_row["statement"],
            "claim_type": claim_row["claim_type"],
            "confidence": claim_row["confidence"],
            "evidence": evidence_items,
        }

    def count_claims(self) -> int:
        """Count registered claims."""
        conn = self.conn_mgr.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM claims;")
        row = cursor.fetchone()
        return row[0] if row else 0
