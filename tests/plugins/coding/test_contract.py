"""Tests for CodingPlugin contract, manifest, and lifecycle."""

import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.coding.manifest import CODING_PLUGIN_MANIFEST
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import CodingInput, CodingResult
from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginHealthStatus,
)
from xeren.plugins.manager import PluginManager


class FailingLLM(MockLLM):
    """Mock LLM that simulates a failing health check."""

    def ping(self) -> bool:
        return False


def test_coding_manifest_metadata():
    """Verify CodingPlugin manifest contains required attributes and capabilities."""
    manifest = CODING_PLUGIN_MANIFEST
    assert manifest.name == "coding"
    assert manifest.version == "0.1.0"
    assert "code generation" in manifest.description.lower()
    assert PluginCapability.CODE_EXECUTION.value in manifest.capabilities
    assert PluginCapability.CODE_GENERATION.value in manifest.capabilities
    assert PluginCapability.CODE_ANALYSIS.value in manifest.capabilities
    assert PluginCapability.SYNTAX_CHECKING.value in manifest.capabilities
    assert PluginCapability.TEST_EXECUTION.value in manifest.capabilities
    assert PluginCapability.CODE_VERIFICATION.value in manifest.capabilities
    assert manifest.input_schema_name == "CodingInput"
    assert manifest.output_schema_name == "CodingResult"


def test_coding_plugin_contract_properties():
    """Verify CodingPlugin conforms to BasePlugin abstract contract."""
    plugin = CodingPlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "coding"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) >= 6
    assert plugin.input_schema is CodingInput
    assert plugin.output_schema is CodingResult


def test_coding_plugin_lifecycle():
    """Verify initialize and shutdown hooks function properly."""
    plugin = CodingPlugin()
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_coding_plugin_health_check_healthy():
    """Verify health check returns HEALTHY status when LLM and sandbox are ready."""
    plugin = CodingPlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["llm_healthy"] is True
    assert health.details["sandbox_active"] is True
    assert health.error is None

    # Test alias
    alias_health = plugin.health()
    assert alias_health.status == PluginHealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_coding_plugin_ahealth_check():
    """Verify asynchronous health check."""
    plugin = CodingPlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY


def test_coding_plugin_health_check_degraded():
    """Verify health check returns DEGRADED when LLM ping fails."""
    plugin = CodingPlugin(llm=FailingLLM())
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.DEGRADED
    assert health.details["llm_healthy"] is False
    assert health.error is not None


def test_coding_plugin_registration_with_manager():
    """Verify CodingPlugin registers and unregisters cleanly with PluginManager."""
    manager = PluginManager()
    plugin = CodingPlugin()
    manager.register(plugin)

    assert manager.has("coding")
    assert manager.get("coding") is plugin

    manifests = manager.list_plugins()
    assert any(m.name == "coding" for m in manifests)

    unregistered = manager.unregister("coding")
    assert unregistered is plugin
    assert not manager.has("coding")
