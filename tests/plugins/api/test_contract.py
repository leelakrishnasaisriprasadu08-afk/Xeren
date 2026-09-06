"""Contract, lifecycle, and registration tests for Xeren API Plugin."""

import pytest

from xeren.plugins.api.manifest import API_PLUGIN_MANIFEST
from xeren.plugins.api.plugin import ApiPlugin
from xeren.plugins.api.schemas import ApiInput, ApiOperation, ApiResult
from xeren.plugins.contract import PluginCapability, PluginHealthStatus
from xeren.plugins.manager import PluginManager


def test_api_manifest_metadata():
    """Verify plugin manifest metadata, version, and capabilities."""
    assert API_PLUGIN_MANIFEST.name == "api"
    assert API_PLUGIN_MANIFEST.version == "0.1.0"
    assert len(API_PLUGIN_MANIFEST.capabilities) == 10

    expected_caps = [
        PluginCapability.API_REQUEST.value,
        PluginCapability.API_RESPONSE.value,
        PluginCapability.API_KEY_AUTHENTICATION.value,
        PluginCapability.API_KEY_ROTATION.value,
        PluginCapability.API_KEY_REVOCATION.value,
        PluginCapability.SCOPED_PERMISSIONS.value,
        PluginCapability.REQUEST_VALIDATION.value,
        PluginCapability.RATE_LIMITING.value,
        PluginCapability.REQUEST_LOGGING.value,
        PluginCapability.HEALTH_STATUS.value,
    ]
    for cap in expected_caps:
        assert cap in API_PLUGIN_MANIFEST.capabilities


def test_api_plugin_contract_properties():
    """Verify ApiPlugin contract compliance."""
    plugin = ApiPlugin()
    assert plugin.name == "api"
    assert plugin.manifest == API_PLUGIN_MANIFEST
    assert plugin.input_schema == ApiInput
    assert plugin.output_schema == ApiResult


def test_api_plugin_lifecycle():
    """Verify initialization, health checks, and shutdown."""
    plugin = ApiPlugin()
    plugin.initialize()
    assert plugin._initialized is True

    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["gateway_ready"] is True
    assert health.details["version"] == "v1"

    plugin.shutdown()
    assert plugin._initialized is False


@pytest.mark.asyncio
async def test_api_plugin_ahealth_check():
    """Verify async health check."""
    plugin = ApiPlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY


def test_api_plugin_manager_registration():
    """Verify registration and execution via PluginManager."""
    manager = PluginManager()
    plugin = ApiPlugin(plugin_manager=manager)
    manager.register(plugin)

    assert manager.has("api")
    retrieved = manager.get("api")
    assert retrieved is plugin

    # Execute health operation via PluginManager
    res = manager.execute(
        "api",
        ApiInput(operation=ApiOperation.HEALTH_STATUS),
    )
    assert res.success is True
    assert isinstance(res.output, ApiResult)
    assert res.output.health_report is not None
    assert res.output.health_report.status == "healthy"
