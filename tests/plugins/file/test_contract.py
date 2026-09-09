"""Tests for FilePlugin contract, manifest, capabilities, and lifecycle."""

import pytest

from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginHealthStatus,
)
from xeren.plugins.file.manifest import FILE_PLUGIN_MANIFEST
from xeren.plugins.file.plugin import FilePlugin
from xeren.plugins.file.schemas import FileInput, FileResult
from xeren.plugins.manager import PluginManager


def test_file_manifest_metadata():
    """Verify FilePlugin manifest contains required attributes and 10 capabilities."""
    manifest = FILE_PLUGIN_MANIFEST
    assert manifest.name == "file"
    assert manifest.version == "0.1.0"
    assert "filesystem" in manifest.description.lower() or "file" in manifest.description.lower()

    # Verify all 10 capabilities
    assert PluginCapability.FILE_READ.value in manifest.capabilities
    assert PluginCapability.FILE_WRITE.value in manifest.capabilities
    assert PluginCapability.FILE_CREATE.value in manifest.capabilities
    assert PluginCapability.FILE_MODIFY.value in manifest.capabilities
    assert PluginCapability.FILE_DELETE.value in manifest.capabilities
    assert PluginCapability.FILE_LIST.value in manifest.capabilities
    assert PluginCapability.FILE_SEARCH.value in manifest.capabilities
    assert PluginCapability.FILE_MOVE.value in manifest.capabilities
    assert PluginCapability.FILE_COPY.value in manifest.capabilities
    assert PluginCapability.FILE_METADATA.value in manifest.capabilities

    # FILE_MOVE_COPY must NOT be in capabilities
    assert "file_move_copy" not in manifest.capabilities

    assert manifest.input_schema_name == "FileInput"
    assert manifest.output_schema_name == "FileResult"


def test_file_plugin_contract_properties(tmp_path):
    """Verify FilePlugin conforms to BasePlugin abstract contract."""
    plugin = FilePlugin(workspace_dir=tmp_path)
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "file"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) == 10
    assert plugin.input_schema is FileInput
    assert plugin.output_schema is FileResult


def test_file_plugin_lifecycle(tmp_path):
    """Verify initialize and shutdown hooks function properly."""
    plugin = FilePlugin(workspace_dir=tmp_path)
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_file_plugin_health_check_healthy(tmp_path):
    """Verify health check returns HEALTHY status when workspace is valid."""
    plugin = FilePlugin(workspace_dir=tmp_path)
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["initialized"] is True
    assert health.details["workspace_exists"] is True
    assert health.details["registered_tools_count"] == 5
    assert health.error is None

    # Test health() alias
    alias_health = plugin.health()
    assert alias_health.status == PluginHealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_file_plugin_ahealth_check(tmp_path):
    """Verify asynchronous health check."""
    plugin = FilePlugin(workspace_dir=tmp_path)
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["tools_ready"] is True


def test_file_plugin_health_check_uninitialized(tmp_path):
    """Verify health check reflects uninitialized state if shutdown."""
    plugin = FilePlugin(workspace_dir=tmp_path)
    plugin.shutdown()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.UNHEALTHY
    assert health.details["initialized"] is False


def test_file_plugin_registration_with_manager(tmp_path):
    """Verify FilePlugin registers cleanly with PluginManager and capability lookups."""
    manager = PluginManager()
    plugin = FilePlugin(workspace_dir=tmp_path)
    manager.register(plugin)

    assert manager.has("file")
    assert manager.get("file") is plugin

    # Look up by capability
    read_plugins = manager.get_by_capability(PluginCapability.FILE_READ)
    assert len(read_plugins) == 1
    assert read_plugins[0] is plugin

    write_plugins = manager.get_by_capability(PluginCapability.FILE_WRITE)
    assert len(write_plugins) == 1
    assert write_plugins[0] is plugin

    manager.unregister("file")
    assert not manager.has("file")
