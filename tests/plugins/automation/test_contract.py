"""Tests for AutomationPlugin contract, manifest, capabilities, and lifecycle."""

import pytest

from xeren.plugins.automation.manifest import AUTOMATION_PLUGIN_MANIFEST
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.automation.schemas import AutomationInput, AutomationOperation, AutomationResult
from xeren.plugins.contract import BasePlugin, PluginCapability, PluginHealthStatus
from xeren.plugins.manager import PluginManager


def test_automation_manifest_metadata():
    """Verify AutomationPlugin manifest contains required attributes and all 10 capabilities."""
    manifest = AUTOMATION_PLUGIN_MANIFEST
    assert manifest.name == "automation"
    assert manifest.version == "0.1.0"
    assert "orchestrat" in manifest.description.lower() or "automation" in manifest.description.lower()

    # Verify all 10 capabilities are present
    assert PluginCapability.TASK_CREATE.value in manifest.capabilities
    assert PluginCapability.TASK_PLAN.value in manifest.capabilities
    assert PluginCapability.TASK_EXECUTE.value in manifest.capabilities
    assert PluginCapability.TASK_PAUSE.value in manifest.capabilities
    assert PluginCapability.TASK_RESUME.value in manifest.capabilities
    assert PluginCapability.TASK_CANCEL.value in manifest.capabilities
    assert PluginCapability.TASK_STATUS.value in manifest.capabilities
    assert PluginCapability.TASK_RETRY.value in manifest.capabilities
    assert PluginCapability.TASK_DEPENDENCY_MANAGEMENT.value in manifest.capabilities
    assert PluginCapability.TASK_HISTORY.value in manifest.capabilities

    assert len(manifest.capabilities) == 10
    assert manifest.input_schema_name == "AutomationInput"
    assert manifest.output_schema_name == "AutomationResult"


def test_automation_plugin_contract_properties():
    """Verify AutomationPlugin conforms to BasePlugin abstract contract."""
    plugin = AutomationPlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "automation"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) == 10
    assert plugin.input_schema is AutomationInput
    assert plugin.output_schema is AutomationResult


def test_automation_plugin_lifecycle():
    """Verify initialize and shutdown hooks update readiness state."""
    plugin = AutomationPlugin()
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_automation_plugin_health_check():
    """Verify synchronous and asynchronous health check reporting."""
    plugin = AutomationPlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.error is None
    assert health.details["initialized"] is True
    assert health.details["tools_ready"] is True
    assert health.details["registered_tools_count"] == 5

    # Also test alias
    alias_health = plugin.health()
    assert alias_health.status == PluginHealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_automation_plugin_ahealth_check():
    """Verify async health check reporting."""
    plugin = AutomationPlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["initialized"] is True


def test_automation_plugin_manager_registration():
    """Verify registration and execution through standard PluginManager."""
    manager = PluginManager()
    plugin = AutomationPlugin(plugin_manager=manager)
    manager.register(plugin)

    assert manager.has("automation")
    retrieved = manager.get("automation")
    assert retrieved is plugin

    # Execute a lightweight task creation via manager
    input_data = AutomationInput(
        operation=AutomationOperation.TASK_CREATE,
        objective="Test manager execution flow",
    )
    res = manager.execute("automation", input_data)
    assert res.success is True
    assert isinstance(res.output, AutomationResult)
    assert res.output.task_id is not None
