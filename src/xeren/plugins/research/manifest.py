"""Manifest definition for the Xeren Research Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

RESEARCH_PLUGIN_MANIFEST = PluginManifest(
    name="research",
    version="0.1.0",
    description="Autonomous research plugin for objective understanding, query generation, web search, source ranking, evidence extraction, and structured findings synthesis.",
    capabilities=[
        PluginCapability.WEB_SEARCH.value,
        PluginCapability.QUERY_GENERATION.value,
        PluginCapability.SOURCE_RANKING.value,
        PluginCapability.EVIDENCE_EXTRACTION.value,
        PluginCapability.SYNTHESIS.value,
    ],
    input_schema_name="ResearchInput",
    output_schema_name="ResearchResult",
    author="Xeren Core Team",
    metadata={
        "category": "information_retrieval",
        "supports_async": True,
        "injectable_search": True,
        "injectable_llm": True,
    },
)

__all__ = ["RESEARCH_PLUGIN_MANIFEST"]
