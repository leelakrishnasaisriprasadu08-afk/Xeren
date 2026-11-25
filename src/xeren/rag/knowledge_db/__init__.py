"""Public API for Xeren Sovereign Knowledge DB subsystem."""

from xeren.rag.knowledge_db.adapter import KnowledgeDBVectorStoreAdapter
from xeren.rag.knowledge_db.api import IKnowledgeDB
from xeren.rag.knowledge_db.client import KnowledgeDBClient
from xeren.rag.knowledge_db.config import KnowledgeDBConfig
from xeren.rag.knowledge_db.indexing.base import IVectorIndexEngine
from xeren.rag.knowledge_db.indexing.local_numpy import NativeLocalVectorIndex
from xeren.rag.knowledge_db.schema.enums import (
    ClaimType,
    HealthState,
    KnowledgeLifecycleState,
    KnowledgeRelationshipType,
    TelemetryPrivacyPolicy,
)
from xeren.rag.knowledge_db.schema.models import (
    BackupManifest,
    ChunkRecord,
    ClaimEvidenceRecord,
    ClaimReceipt,
    ClaimRecord,
    DocumentRecord,
    DocumentVersionRecord,
    EmbeddingRecord,
    IngestionReceipt,
    KnowledgeDBHealth,
    KnowledgeRelationshipRecord,
    KnowledgeRetrievalItem,
    KnowledgeRetrievalResult,
    ProvenanceRecord,
    RetrievalEventRecord,
    SourceRecord,
)

__all__ = [
    # Interfaces & Clients
    "IKnowledgeDB",
    "KnowledgeDBClient",
    "KnowledgeDBConfig",
    "KnowledgeDBVectorStoreAdapter",
    "IVectorIndexEngine",
    "NativeLocalVectorIndex",
    # Enums
    "KnowledgeLifecycleState",
    "KnowledgeRelationshipType",
    "ClaimType",
    "TelemetryPrivacyPolicy",
    "HealthState",
    # Receipts & Result Models
    "IngestionReceipt",
    "ClaimReceipt",
    "KnowledgeRetrievalResult",
    "KnowledgeRetrievalItem",
    "KnowledgeDBHealth",
    "BackupManifest",
    # Schema Records
    "SourceRecord",
    "DocumentRecord",
    "DocumentVersionRecord",
    "ChunkRecord",
    "KnowledgeRelationshipRecord",
    "ClaimRecord",
    "ClaimEvidenceRecord",
    "ProvenanceRecord",
    "RetrievalEventRecord",
    "EmbeddingRecord",
]
