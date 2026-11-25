"""Tests for DataPlugin contract, manifest, capabilities, and lifecycle."""

import pytest

from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginHealthStatus,
)
from xeren.plugins.data.manifest import DATA_PLUGIN_MANIFEST
from xeren.plugins.data.plugin import DataPlugin
from xeren.plugins.data.schemas import DataInput, DataResult
from xeren.plugins.manager import PluginManager


def test_data_manifest_metadata():
    """Verify DataPlugin manifest contains required attributes and capabilities."""
    manifest = DATA_PLUGIN_MANIFEST
    assert manifest.name == "data"
    assert manifest.version == "0.1.0"
    assert "data" in manifest.description.lower()
    assert PluginCapability.DATA_INGESTION.value in manifest.capabilities
    assert PluginCapability.DATA_INSPECTION.value in manifest.capabilities
    assert PluginCapability.DATA_CLEANING.value in manifest.capabilities
    assert PluginCapability.DATA_TRANSFORMATION.value in manifest.capabilities
    assert PluginCapability.DATA_ANALYSIS.value in manifest.capabilities
    assert PluginCapability.DATA_VISUALIZATION.value in manifest.capabilities
    assert PluginCapability.DATA_VERIFICATION.value in manifest.capabilities
    assert manifest.input_schema_name == "DataInput"
    assert manifest.output_schema_name == "DataResult"


def test_data_plugin_contract_properties():
    """Verify DataPlugin conforms to BasePlugin abstract contract."""
    plugin = DataPlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "data"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) == 7
    assert plugin.input_schema is DataInput
    assert plugin.output_schema is DataResult


def test_data_plugin_lifecycle():
    """Verify initialize and shutdown hooks function properly."""
    plugin = DataPlugin()
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_data_plugin_health_check_healthy():
    """Verify health check returns HEALTHY status when tools are ready."""
    plugin = DataPlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["initialized"] is True
    assert health.details["tools_ready"] is True
    assert health.details["registered_tools_count"] == 7
    assert health.error is None

    # Test alias
    alias_health = plugin.health()
    assert alias_health.status == PluginHealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_data_plugin_ahealth_check():
    """Verify asynchronous health check."""
    plugin = DataPlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["tools_ready"] is True


def test_data_plugin_health_check_uninitialized():
    """Verify health check reflects uninitialized state if shutdown."""
    plugin = DataPlugin()
    plugin.shutdown()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.UNHEALTHY
    assert health.details["initialized"] is False


def test_data_plugin_registration_with_manager():
    """Verify DataPlugin registers and unregisters cleanly with PluginManager."""
    manager = PluginManager()
    plugin = DataPlugin()
    manager.register(plugin)

    assert manager.has("data")
    assert manager.get("data") is plugin

    # Verify lookup by capability
    ingest_plugins = manager.get_by_capability(PluginCapability.DATA_INGESTION)
    assert len(ingest_plugins) == 1
    assert ingest_plugins[0] is plugin

    analysis_plugins = manager.get_by_capability(PluginCapability.DATA_ANALYSIS)
    assert len(analysis_plugins) == 1
    assert analysis_plugins[0] is plugin

    manager.unregister("data")
    assert not manager.has("data")
