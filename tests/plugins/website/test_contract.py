"""Tests for WebsitePlugin contract, manifest, capabilities, and lifecycle."""

import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginHealthStatus,
)
from xeren.plugins.manager import PluginManager
from xeren.plugins.website.manifest import WEBSITE_PLUGIN_MANIFEST
from xeren.plugins.website.plugin import WebsitePlugin
from xeren.plugins.website.schemas import WebsiteInput, WebsiteResult


class FailingLLM(MockLLM):
    """Mock LLM that simulates health check ping failure."""

    def ping(self) -> bool:
        return False


def test_website_manifest_metadata():
    """Verify WebsitePlugin manifest contains required attributes and capabilities."""
    manifest = WEBSITE_PLUGIN_MANIFEST
    assert manifest.name == "website"
    assert manifest.version == "0.1.0"
    assert "website" in manifest.description.lower()
    assert PluginCapability.WEBSITE_REQUIREMENT_ANALYSIS.value in manifest.capabilities
    assert PluginCapability.WEBSITE_GENERATION.value in manifest.capabilities
    assert PluginCapability.WEBSITE_MODIFICATION.value in manifest.capabilities
    assert PluginCapability.WEBSITE_VALIDATION.value in manifest.capabilities
    assert PluginCapability.WEBSITE_SECURITY_CHECK.value in manifest.capabilities
    assert PluginCapability.WEBSITE_PREVIEW.value in manifest.capabilities
    assert manifest.input_schema_name == "WebsiteInput"
    assert manifest.output_schema_name == "WebsiteResult"


def test_website_plugin_contract_properties():
    """Verify WebsitePlugin conforms to BasePlugin abstract contract."""
    plugin = WebsitePlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "website"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) == 6
    assert plugin.input_schema is WebsiteInput
    assert plugin.output_schema is WebsiteResult


def test_website_plugin_lifecycle():
    """Verify initialize and shutdown hooks function properly."""
    plugin = WebsitePlugin()
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_website_plugin_health_check_healthy():
    """Verify health check returns HEALTHY status when LLM and coding plugin are ready."""
    plugin = WebsitePlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["llm_healthy"] is True
    assert health.details["coding_plugin_healthy"] is True
    assert health.error is None

    # Test alias
    alias_health = plugin.health()
    assert alias_health.status == PluginHealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_website_plugin_ahealth_check():
    """Verify asynchronous health check."""
    plugin = WebsitePlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY


def test_website_plugin_health_check_degraded():
    """Verify health check returns DEGRADED when LLM ping fails."""
    plugin = WebsitePlugin(llm=FailingLLM())
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.DEGRADED
    assert health.details["llm_healthy"] is False
    assert health.error is not None


def test_website_plugin_registration_with_manager():
    """Verify WebsitePlugin registers and unregisters cleanly with PluginManager."""
    manager = PluginManager()
    plugin = WebsitePlugin()
    manager.register(plugin)

    assert manager.has("website")
    assert manager.get("website") is plugin

    manifests = manager.list_plugins()
    assert any(m.name == "website" for m in manifests)

    unregistered = manager.unregister("website")
    assert unregistered is plugin
    assert not manager.has("website")
