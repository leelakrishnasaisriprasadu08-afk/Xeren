"""Manifest metadata for the Xeren Knowledge/RAG Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

KNOWLEDGE_PLUGIN_MANIFEST = PluginManifest(
    name="knowledge",
    version="0.1.0",
    description="Knowledge and RAG plugin providing document ingestion, vector retrieval, BM25 keyword search, hybrid fusion, reranking, and grounded context construction with provenance.",
    capabilities=[
        PluginCapability.KNOWLEDGE_RETRIEVAL.value,
        PluginCapability.KNOWLEDGE_INGESTION.value,
        PluginCapability.CONTEXT_BUILDING.value,
        PluginCapability.RERANKING.value,
        PluginCapability.SOURCE_RANKING.value,
    ],
    input_schema_name="KnowledgeInput",
    output_schema_name="KnowledgeResult",
    author="Xeren Core Team",
    metadata={
        "category": "retrieval_augmented_generation",
        "supports_hybrid": True,
        "supports_ingestion": True,
        "preserves_provenance": True,
    },
)

__all__ = ["KNOWLEDGE_PLUGIN_MANIFEST"]
