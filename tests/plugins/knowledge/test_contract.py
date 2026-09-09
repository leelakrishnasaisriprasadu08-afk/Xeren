"""Tests for KnowledgePlugin contract, lifecycle, and registration."""

import pytest

from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginHealthStatus,
)
from xeren.plugins.knowledge.manifest import KNOWLEDGE_PLUGIN_MANIFEST
from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.schemas import KnowledgeInput, KnowledgeResult
from xeren.plugins.manager import PluginManager
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel


class FailingEmbeddingModel(MockEmbeddingModel):
    """Test embedding model that simulates failure on ping."""

    def ping(self) -> bool:
        return False


def test_knowledge_manifest_metadata():
    """Verify manifest metadata complies with plugin standards."""
    manifest = KNOWLEDGE_PLUGIN_MANIFEST
    assert manifest.name == "knowledge"
    assert manifest.version == "0.1.0"
    assert "retrieval" in manifest.description.lower()
    assert PluginCapability.KNOWLEDGE_RETRIEVAL.value in manifest.capabilities
    assert PluginCapability.KNOWLEDGE_INGESTION.value in manifest.capabilities
    assert PluginCapability.CONTEXT_BUILDING.value in manifest.capabilities
    assert PluginCapability.RERANKING.value in manifest.capabilities
    assert manifest.input_schema_name == "KnowledgeInput"
    assert manifest.output_schema_name == "KnowledgeResult"


def test_knowledge_plugin_contract_properties():
    """Verify KnowledgePlugin exposes all BasePlugin abstract properties."""
    plugin = KnowledgePlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "knowledge"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) >= 4
    assert plugin.input_schema is KnowledgeInput
    assert plugin.output_schema is KnowledgeResult


def test_knowledge_plugin_lifecycle():
    """Verify initialize and shutdown hooks function properly."""
    plugin = KnowledgePlugin()
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_knowledge_plugin_health_check_healthy():
    """Verify health check returns HEALTHY status when dependencies are functioning."""
    plugin = KnowledgePlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["embedding_healthy"] is True
    assert health.details["indexed_vector_chunks"] == 0
    assert health.error is None

    # Test health alias
    alias_health = plugin.health()
    assert alias_health.status == PluginHealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_knowledge_plugin_ahealth_check():
    """Verify asynchronous health check."""
    plugin = KnowledgePlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY


def test_knowledge_plugin_health_check_degraded():
    """Verify health check returns DEGRADED when embedding model fails."""
    plugin = KnowledgePlugin(embedding_model=FailingEmbeddingModel())
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.DEGRADED
    assert health.details["embedding_healthy"] is False
    assert health.error is not None


def test_knowledge_plugin_registration_with_manager():
    """Verify KnowledgePlugin integrates cleanly with PluginManager."""
    manager = PluginManager()
    plugin = KnowledgePlugin()
    manager.register(plugin)

    assert manager.has("knowledge")
    assert manager.get("knowledge") is plugin

    manifests = manager.list_plugins()
    assert any(m.name == "knowledge" for m in manifests)

    unregistered = manager.unregister("knowledge")
    assert unregistered is plugin
    assert not manager.has("knowledge")
