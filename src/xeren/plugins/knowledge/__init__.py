"""Xeren Knowledge / RAG Plugin.

Exposes modular document ingestion, vector retrieval, BM25 keyword search,
hybrid fusion, reranking, and grounded context construction with provenance.
"""

from xeren.plugins.knowledge.manifest import KNOWLEDGE_PLUGIN_MANIFEST
from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.registry import KnowledgeToolRegistry
from xeren.plugins.knowledge.schemas import (
    KnowledgeInput,
    KnowledgeOperation,
    KnowledgeResult,
    RetrievalMode,
)
from xeren.plugins.knowledge.workflow import KnowledgeWorkflow

__all__ = [
    "KnowledgePlugin",
    "KNOWLEDGE_PLUGIN_MANIFEST",
    "KnowledgeInput",
    "KnowledgeResult",
    "KnowledgeOperation",
    "RetrievalMode",
    "KnowledgeWorkflow",
    "KnowledgeToolRegistry",
]

