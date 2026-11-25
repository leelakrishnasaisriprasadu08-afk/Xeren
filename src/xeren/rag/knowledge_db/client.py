"""KnowledgeDBClient implementing IKnowledgeDB with modular manager coordination."""

import hashlib
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from xeren.rag.document import DocumentChunk
from xeren.rag.knowledge_db.api import IKnowledgeDB
from xeren.rag.knowledge_db.backup.manifest import load_manifest
from xeren.rag.knowledge_db.backup.recovery import RecoveryManager
from xeren.rag.knowledge_db.backup.snapshot import SnapshotManager
from xeren.rag.knowledge_db.config import KnowledgeDBConfig
from xeren.rag.knowledge_db.indexing.base import IVectorIndexEngine
from xeren.rag.knowledge_db.indexing.local_numpy import NativeLocalVectorIndex
from xeren.rag.knowledge_db.managers.document import DocumentManager
from xeren.rag.knowledge_db.managers.evidence import EvidenceManager
from xeren.rag.knowledge_db.managers.graph import GraphManager
from xeren.rag.knowledge_db.managers.lexical import LexicalIndexManager
from xeren.rag.knowledge_db.managers.lifecycle import LifecycleManager
from xeren.rag.knowledge_db.managers.metadata import MetadataManager
from xeren.rag.knowledge_db.managers.telemetry import RetrievalTelemetryManager
from xeren.rag.knowledge_db.managers.vector import VectorIndexManager
from xeren.rag.knowledge_db.schema.enums import (
    ClaimType,
    HealthState,
    KnowledgeLifecycleState,
    KnowledgeRelationshipType,
)
from xeren.rag.knowledge_db.schema.models import (
    BackupManifest,
    ClaimReceipt,
    IngestionReceipt,
    KnowledgeDBHealth,
    KnowledgeRetrievalItem,
    KnowledgeRetrievalResult,
    ProvenanceRecord,
)
from xeren.rag.knowledge_db.storage.connection import ConnectionManager
from xeren.rag.retrieval.filter import MetadataFilter


class KnowledgeDBClient(IKnowledgeDB):
    """Authoritative client for Xeren Sovereign Knowledge Database subsystem."""

    def __init__(
        self,
        config: Optional[KnowledgeDBConfig] = None,
        vector_engine: Optional[IVectorIndexEngine] = None,
    ) -> None:
        self.config = config or KnowledgeDBConfig()
        self.config.ensure_directories()

        # Connection and Index Engines
        self.conn_mgr = ConnectionManager(self.config.primary_db_path, self.config)
        self.vector_engine = vector_engine or NativeLocalVectorIndex(self.config.primary_indexes_dir)

        # Domain Managers
        self.metadata_mgr = MetadataManager(self.conn_mgr)
        self.doc_mgr = DocumentManager(self.config)
        self.vector_mgr = VectorIndexManager(self.conn_mgr, self.vector_engine)
        self.lexical_mgr = LexicalIndexManager(self.conn_mgr)
        self.graph_mgr = GraphManager(self.conn_mgr)
        self.evidence_mgr = EvidenceManager(self.conn_mgr)
        self.lifecycle_mgr = LifecycleManager(self.conn_mgr)
        self.telemetry_mgr = RetrievalTelemetryManager(self.conn_mgr, self.config.telemetry_policy)

        # Backup & Recovery Managers
        self.snapshot_mgr = SnapshotManager(self.config, self.conn_mgr, self.vector_engine)
        self.recovery_mgr = RecoveryManager(self.config, self.conn_mgr, self.vector_engine)

    def ingest_document(
        self,
        source_uri: str,
        content: str,
        title: Optional[str] = None,
        source_type: str = "file",
        workspace_id: str = "default",
        access_level: str = "LIBERAL",
        sensitivity_tier: str = "INTERNAL",
        embedding_vector: Optional[List[float]] = None,
        embedding_model_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestionReceipt:
        """Store source, stage document, decompose chunks, index vectors/tokens, and record provenance."""
        start_time = time.perf_counter()
        meta_dict = metadata or {}

        # 1. Source and Content Hash
        content_hash = self.doc_mgr.compute_hash(content)
        source = self.metadata_mgr.get_or_create_source(source_uri=source_uri, source_type=source_type)

        # 2. Register Root Document
        doc = self.metadata_mgr.create_document(
            source_id=source.source_id,
            content_hash=content_hash,
            title=title,
            workspace_id=workspace_id,
            access_level=access_level,
            sensitivity_tier=sensitivity_tier,
        )

        # 3. Store raw text file
        rel_path = self.doc_mgr.store_document_content(
            document_id=doc.document_id,
            version=1,
            content=content,
        )
        self.metadata_mgr.create_version(
            document_id=doc.document_id,
            version_number=1,
            content_path=rel_path,
            content_hash=content_hash,
            change_summary="Initial ingestion",
        )

        # 4. Decompose content into Chunks
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [content]

        created_chunks: List[str] = []
        embeddings_created = 0

        with self.conn_mgr.transaction() as conn:
            for idx, para in enumerate(paragraphs):
                chunk_id = f"chk_{doc.document_id[:8]}_{idx}"
                c_hash = hashlib.sha256(para.encode("utf-8")).hexdigest()
                tokens = max(1, len(para) // 4)

                conn.execute(
                    """
                    INSERT INTO chunks (
                        chunk_id, document_id, version_number, chunk_index,
                        content, token_count, section_title, page_number,
                        parent_chunk_id, content_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        chunk_id,
                        doc.document_id,
                        1,
                        idx,
                        para,
                        tokens,
                        meta_dict.get("section"),
                        meta_dict.get("page"),
                        meta_dict.get("parent_chunk_id"),
                        c_hash,
                        time.time(),
                    ),
                )
                created_chunks.append(chunk_id)

                # Index lexical terms
                self.lexical_mgr.index_chunk_terms(chunk_id, para)

                # Record Provenance Link
                self.evidence_mgr.record_provenance(
                    chunk_id=chunk_id,
                    document_id=doc.document_id,
                    source_uri=source_uri,
                    document_version=1,
                    page_number=meta_dict.get("page"),
                )

                # Record Embedding if provided
                if embedding_vector and embedding_model_id:
                    self.vector_mgr.record_embedding(
                        chunk_id=chunk_id,
                        model_id=embedding_model_id,
                        vector=embedding_vector,
                    )
                    embeddings_created += 1

        # 5. Advance Lifecycle State: INGESTED -> PROCESSED -> INDEXED -> ACTIVE
        self.lifecycle_mgr.transition_state(doc.document_id, KnowledgeLifecycleState.PROCESSED)
        self.lifecycle_mgr.transition_state(doc.document_id, KnowledgeLifecycleState.INDEXED)
        self.lifecycle_mgr.transition_state(doc.document_id, KnowledgeLifecycleState.VALIDATED)
        self.lifecycle_mgr.transition_state(doc.document_id, KnowledgeLifecycleState.ACTIVE)

        # 6. Checkpoint if configured
        if self.config.auto_backup_on_ingest:
            self.create_backup_checkpoint()

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return IngestionReceipt(
            document_id=doc.document_id,
            source_id=source.source_id,
            source_uri=source_uri,
            version=1,
            chunks_created=len(created_chunks),
            embeddings_created=embeddings_created,
            content_hash=content_hash,
            lifecycle_state=KnowledgeLifecycleState.ACTIVE,
            elapsed_ms=elapsed_ms,
        )

    def record_relationship(
        self,
        source_chunk_id: str,
        target_chunk_id: str,
        relationship_type: KnowledgeRelationshipType,
        confidence: float = 1.0,
        evidence_reference: Optional[str] = None,
        model_id: str = "xeren_ingest",
        created_by: str = "system",
    ) -> str:
        """Create a semantic knowledge graph edge linking two chunks."""
        rel = self.graph_mgr.add_relationship(
            source_chunk_id=source_chunk_id,
            target_chunk_id=target_chunk_id,
            relationship_type=relationship_type,
            confidence=confidence,
            evidence_reference=evidence_reference,
            model_id=model_id,
            created_by=created_by,
        )
        return rel.relationship_id

    def record_claim(
        self,
        statement: str,
        supporting_chunk_ids: List[str],
        claim_type: ClaimType = ClaimType.FACT,
        confidence: float = 1.0,
    ) -> ClaimReceipt:
        """Register a verifiable claim and link supporting chunk evidence."""
        return self.evidence_mgr.record_claim(
            statement=statement,
            supporting_chunk_ids=supporting_chunk_ids,
            claim_type=claim_type,
            confidence=confidence,
        )

    def retrieve(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        model_id: Optional[str] = None,
        top_k: int = 5,
        workspace_id: str = "default",
        allowed_access_levels: Optional[Set[str]] = None,
        include_relationships: bool = True,
        filter: Optional[MetadataFilter] = None,
    ) -> KnowledgeRetrievalResult:
        """Execute hybrid search, verify workspace isolation, expand graph relations, and log telemetry."""
        start_time = time.perf_counter()
        query_id = str(uuid.uuid4())
        q_norm = query.strip().lower()
        q_hash = hashlib.sha256(q_norm.encode("utf-8")).hexdigest()

        # Step 1: Pre-filter candidate chunks based on Workspace and Access Levels
        conn = self.conn_mgr.get_connection()
        allowed_levels = allowed_access_levels or {"LIBERAL", "SENSITIVE"}
        placeholders = ",".join("?" for _ in allowed_levels)
        cursor = conn.execute(
            f"""
            SELECT c.chunk_id
            FROM chunks c
            JOIN documents d ON c.document_id = d.document_id
            WHERE d.workspace_id = ?
              AND d.access_level IN ({placeholders})
              AND d.lifecycle_state = 'ACTIVE';
            """,
            [workspace_id, *allowed_levels],
        )
        authorized_chunk_ids = {row[0] for row in cursor.fetchall()}

        if not authorized_chunk_ids:
            return KnowledgeRetrievalResult(
                query_id=query_id,
                query_hash=q_hash,
                items=[],
                total_candidates_found=0,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                workspace_id=workspace_id,
            )

        # Step 2: Dense Vector Retrieval (if vector provided)
        dense_scores: Dict[str, float] = {}
        if query_vector and model_id:
            dense_hits = self.vector_mgr.search_vectors(
                model_id=model_id,
                query_vector=query_vector,
                top_k=top_k * 3,
                candidate_chunk_ids=authorized_chunk_ids,
            )
            dense_scores = dict(dense_hits)

        # Step 3: Sparse Lexical Retrieval (BM25)
        lexical_hits = self.lexical_mgr.search_lexical(
            query=query,
            top_k=top_k * 3,
            candidate_chunk_ids=authorized_chunk_ids,
        )
        lexical_scores = dict(lexical_hits)

        # Step 4: Reciprocal Rank Fusion (RRF)
        rrf_k = 60.0
        combined_scores: Dict[str, float] = {}

        # Rank dense
        sorted_dense = sorted(dense_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (cid, _) in enumerate(sorted_dense, start=1):
            combined_scores[cid] = combined_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        # Rank lexical
        sorted_lex = sorted(lexical_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (cid, _) in enumerate(sorted_lex, start=1):
            combined_scores[cid] = combined_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        if not combined_scores:
            return KnowledgeRetrievalResult(
                query_id=query_id,
                query_hash=q_hash,
                items=[],
                total_candidates_found=0,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                workspace_id=workspace_id,
            )

        ranked_cids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]


        # Step 5: Hydrate chunks, graph relationships, and provenance
        items: List[KnowledgeRetrievalItem] = []
        for rank_pos, (cid, score) in enumerate(ranked_cids, start=1):
            chunk_row = conn.execute(
                """
                SELECT c.*, d.title as doc_title, s.source_uri
                FROM chunks c
                JOIN documents d ON c.document_id = d.document_id
                JOIN sources s ON d.source_id = s.source_id
                WHERE c.chunk_id = ?;
                """,
                (cid,),
            ).fetchone()

            if not chunk_row:
                continue

            metadata = {
                "source": chunk_row["source_uri"],
                "title": chunk_row["doc_title"],
                "section": chunk_row["section_title"],
                "page": chunk_row["page_number"],
                "workspace_id": workspace_id,
            }

            doc_chunk = DocumentChunk(
                chunk_id=chunk_row["chunk_id"],
                document_id=chunk_row["document_id"],
                content=chunk_row["content"],
                chunk_index=chunk_row["chunk_index"],
                metadata=metadata,
            )

            # Optional metadata filter
            if filter and not filter.matches(metadata):
                continue

            # Relationships
            relations = (
                self.graph_mgr.get_relationships(cid) if include_relationships else []
            )

            # Provenance
            prov_row = conn.execute(
                "SELECT * FROM provenance WHERE chunk_id = ? LIMIT 1;", (cid,)
            ).fetchone()
            prov = (
                ProvenanceRecord(
                    provenance_id=prov_row["provenance_id"],
                    claim_id=prov_row["claim_id"],
                    chunk_id=prov_row["chunk_id"],
                    document_id=prov_row["document_id"],
                    source_uri=prov_row["source_uri"],
                    document_version=prov_row["document_version"],
                    page_number=prov_row["page_number"],
                    recorded_at=prov_row["recorded_at"],
                )
                if prov_row
                else None
            )

            retrieval_method = "hybrid_rrf"
            if cid in dense_scores and cid not in lexical_scores:
                retrieval_method = "dense_vector"
            elif cid in lexical_scores and cid not in dense_scores:
                retrieval_method = "bm25_lexical"

            # Log Telemetry
            self.telemetry_mgr.record_event(
                query_id=query_id,
                query_text=query,
                chunk_id=cid,
                retrieval_method=retrieval_method,
                rank_position=rank_pos,
                score=score,
                workspace_id=workspace_id,
            )

            items.append(
                KnowledgeRetrievalItem(
                    chunk=doc_chunk,
                    score=score,
                    retrieval_method=retrieval_method,
                    relationships=relations,
                    provenance=prov,
                )
            )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return KnowledgeRetrievalResult(
            query_id=query_id,
            query_hash=q_hash,
            items=items,
            total_candidates_found=len(combined_scores),
            latency_ms=latency_ms,
            workspace_id=workspace_id,
        )

    def transition_lifecycle(
        self,
        document_id: str,
        target_state: KnowledgeLifecycleState,
        reason: Optional[str] = None,
        superseded_by: Optional[str] = None,
    ) -> None:
        """Safely transition document lifecycle state enforcing the valid state machine."""
        if target_state == KnowledgeLifecycleState.SUPERSEDED and superseded_by:
            self.lifecycle_mgr.supersede_document(document_id, superseded_by)
        else:
            self.lifecycle_mgr.transition_state(document_id, target_state, reason=reason)

    def create_backup_checkpoint(self) -> BackupManifest:
        """Trigger an online, transaction-safe snapshot to the passive backup store."""
        return self.snapshot_mgr.create_snapshot()

    def restore_from_backup(self) -> bool:
        """Restore primary database from verified passive backup manifest."""
        return self.recovery_mgr.restore_from_backup()

    def health_check(self) -> KnowledgeDBHealth:
        """Inspect health status of primary and backup stores."""
        primary_st = self.recovery_mgr.inspect_health()
        backup_st = self.recovery_mgr.inspect_backup_health()

        p_size = self.config.primary_db_path.stat().st_size if self.config.primary_db_path.exists() else 0
        doc_cnt = 0
        rel_cnt = 0
        claim_cnt = 0
        chunk_cnt = 0

        if primary_st == HealthState.PRIMARY_HEALTHY:
            try:
                doc_cnt = self.metadata_mgr.count_documents()
                rel_cnt = self.graph_mgr.count_relationships()
                claim_cnt = self.evidence_mgr.count_claims()
                conn = self.conn_mgr.get_connection()
                chunk_row = conn.execute("SELECT COUNT(*) FROM chunks;").fetchone()
                chunk_cnt = chunk_row[0] if chunk_row else 0
            except Exception:
                primary_st = HealthState.PRIMARY_CORRUPTED

        latest_man = load_manifest(self.config.manifests_dir / "latest_manifest.json")
        backup_ts = latest_man.created_at if latest_man else None

        diagnostics = []
        if primary_st == HealthState.PRIMARY_CORRUPTED:
            diagnostics.append("Primary database integrity check failed.")
        if backup_st == HealthState.BACKUP_INVALID:
            diagnostics.append("Backup manifest or directory verification failed.")

        return KnowledgeDBHealth(
            primary_state=primary_st,
            backup_state=backup_st,
            primary_db_size_bytes=p_size,
            total_documents=doc_cnt,
            total_chunks=chunk_cnt,
            total_relationships=rel_cnt,
            total_claims=claim_cnt,
            last_backup_timestamp=backup_ts,
            diagnostics=diagnostics,
        )

