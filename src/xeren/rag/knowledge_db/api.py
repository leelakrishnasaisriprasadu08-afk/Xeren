"""Abstract public interface for Xeren Sovereign Knowledge DB subsystem."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from xeren.rag.knowledge_db.schema.enums import (
    ClaimType,
    KnowledgeLifecycleState,
    KnowledgeRelationshipType,
)
from xeren.rag.knowledge_db.schema.models import (
    BackupManifest,
    ClaimReceipt,
    IngestionReceipt,
    KnowledgeDBHealth,
    KnowledgeRetrievalResult,
)
from xeren.rag.retrieval.filter import MetadataFilter


class IKnowledgeDB(ABC):
    """Core authoritative API contract for the Knowledge DB subsystem."""

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def record_claim(
        self,
        statement: str,
        supporting_chunk_ids: List[str],
        claim_type: ClaimType = ClaimType.FACT,
        confidence: float = 1.0,
    ) -> ClaimReceipt:
        """Register a verifiable claim and link supporting chunk evidence."""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def transition_lifecycle(
        self,
        document_id: str,
        target_state: KnowledgeLifecycleState,
        reason: Optional[str] = None,
        superseded_by: Optional[str] = None,
    ) -> None:
        """Safely transition document lifecycle state enforcing the valid state machine."""
        pass

    @abstractmethod
    def create_backup_checkpoint(self) -> BackupManifest:
        """Trigger an online, transaction-safe snapshot to the passive backup store."""
        pass

    @abstractmethod
    def restore_from_backup(self) -> bool:
        """Restore primary database from verified passive backup manifest."""
        pass

    @abstractmethod
    def health_check(self) -> KnowledgeDBHealth:
        """Inspect health status of primary and backup stores."""
        pass
