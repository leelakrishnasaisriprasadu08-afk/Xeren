"""MetadataManager handling sources, documents, and versions in SQLite."""

import sqlite3
import time
from typing import List, Optional
from xeren.rag.knowledge_db.schema.enums import KnowledgeLifecycleState
from xeren.rag.knowledge_db.schema.models import DocumentRecord, DocumentVersionRecord, SourceRecord
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class MetadataManager:
    """Manages relational entities for Source Layer in SQLite."""

    def __init__(self, connection_mgr: ConnectionManager) -> None:
        self.conn_mgr = connection_mgr

    def get_or_create_source(self, source_uri: str, source_type: str = "file") -> SourceRecord:
        """Find existing source by URI or create a new one."""
        with self.conn_mgr.transaction() as conn:
            cursor = conn.execute(
                "SELECT source_id, source_type, source_uri, created_at, updated_at FROM sources WHERE source_uri = ?;",
                (source_uri,),
            )
            row = cursor.fetchone()
            if row:
                return SourceRecord(
                    source_id=row["source_id"],
                    source_type=row["source_type"],
                    source_uri=row["source_uri"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

            record = SourceRecord(source_type=source_type, source_uri=source_uri)
            conn.execute(
                "INSERT INTO sources (source_id, source_type, source_uri, created_at, updated_at) VALUES (?, ?, ?, ?, ?);",
                (record.source_id, record.source_type, record.source_uri, record.created_at, record.updated_at),
            )
            return record

    def create_document(
        self,
        source_id: str,
        content_hash: str,
        title: Optional[str] = None,
        workspace_id: str = "default",
        access_level: str = "LIBERAL",
        sensitivity_tier: str = "INTERNAL",
        retention_policy: str = "FOREVER",
    ) -> DocumentRecord:
        """Create a new root document record in the INGESTED state."""
        doc = DocumentRecord(
            source_id=source_id,
            title=title,
            content_hash=content_hash,
            current_version=1,
            lifecycle_state=KnowledgeLifecycleState.INGESTED,
            workspace_id=workspace_id,
            access_level=access_level,
            sensitivity_tier=sensitivity_tier,
            retention_policy=retention_policy,
        )
        with self.conn_mgr.transaction() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    document_id, source_id, title, content_hash, current_version,
                    lifecycle_state, owner, workspace_id, access_level, sensitivity_tier,
                    retention_policy, superseded_by_doc_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    doc.document_id,
                    doc.source_id,
                    doc.title,
                    doc.content_hash,
                    doc.current_version,
                    doc.lifecycle_state.value,
                    doc.owner,
                    doc.workspace_id,
                    doc.access_level,
                    doc.sensitivity_tier,
                    doc.retention_policy,
                    doc.superseded_by_doc_id,
                    doc.created_at,
                    doc.updated_at,
                ),
            )
        return doc

    def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """Fetch document record by primary ID."""
        conn = self.conn_mgr.get_connection()
        cursor = conn.execute(
            """
            SELECT document_id, source_id, title, content_hash, current_version,
                   lifecycle_state, owner, workspace_id, access_level, sensitivity_tier,
                   retention_policy, superseded_by_doc_id, created_at, updated_at
            FROM documents WHERE document_id = ?;
            """,
            (document_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return DocumentRecord(
            document_id=row["document_id"],
            source_id=row["source_id"],
            title=row["title"],
            content_hash=row["content_hash"],
            current_version=row["current_version"],
            lifecycle_state=KnowledgeLifecycleState(row["lifecycle_state"]),
            owner=row["owner"],
            workspace_id=row["workspace_id"],
            access_level=row["access_level"],
            sensitivity_tier=row["sensitivity_tier"],
            retention_policy=row["retention_policy"],
            superseded_by_doc_id=row["superseded_by_doc_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_version(
        self,
        document_id: str,
        version_number: int,
        content_path: str,
        content_hash: str,
        change_summary: Optional[str] = None,
    ) -> DocumentVersionRecord:
        """Create an immutable version snapshot."""
        ver = DocumentVersionRecord(
            document_id=document_id,
            version_number=version_number,
            content_path=content_path,
            content_hash=content_hash,
            change_summary=change_summary,
        )
        with self.conn_mgr.transaction() as conn:
            conn.execute(
                """
                INSERT INTO document_versions (
                    version_id, document_id, version_number, content_path,
                    content_hash, change_summary, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ver.version_id,
                    ver.document_id,
                    ver.version_number,
                    ver.content_path,
                    ver.content_hash,
                    ver.change_summary,
                    ver.created_at,
                ),
            )
        return ver

    def list_documents(
        self,
        workspace_id: Optional[str] = None,
        lifecycle_state: Optional[KnowledgeLifecycleState] = None,
    ) -> List[DocumentRecord]:
        """Query documents with optional workspace or state filtering."""
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        if workspace_id:
            query += " AND workspace_id = ?"
            params.append(workspace_id)
        if lifecycle_state:
            query += " AND lifecycle_state = ?"
            params.append(lifecycle_state.value)
        query += " ORDER BY updated_at DESC;"

        conn = self.conn_mgr.get_connection()
        cursor = conn.execute(query, tuple(params))
        results: List[DocumentRecord] = []
        for row in cursor.fetchall():
            results.append(
                DocumentRecord(
                    document_id=row["document_id"],
                    source_id=row["source_id"],
                    title=row["title"],
                    content_hash=row["content_hash"],
                    current_version=row["current_version"],
                    lifecycle_state=KnowledgeLifecycleState(row["lifecycle_state"]),
                    owner=row["owner"],
                    workspace_id=row["workspace_id"],
                    access_level=row["access_level"],
                    sensitivity_tier=row["sensitivity_tier"],
                    retention_policy=row["retention_policy"],
                    superseded_by_doc_id=row["superseded_by_doc_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return results

    def count_documents(self) -> int:
        """Total documents registered."""
        conn = self.conn_mgr.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM documents;")
        row = cursor.fetchone()
        return row[0] if row else 0
