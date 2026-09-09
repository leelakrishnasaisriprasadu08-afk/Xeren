"""Tests for VerificationPlugin contract, manifest, capabilities, and lifecycle."""

import pytest

from xeren.plugins.contract import BasePlugin, PluginCapability, PluginHealthStatus
from xeren.plugins.manager import PluginManager
from xeren.plugins.verification.manifest import VERIFICATION_PLUGIN_MANIFEST
from xeren.plugins.verification.plugin import VerificationPlugin
from xeren.plugins.verification.schemas import VerificationInput, VerificationResult


def test_verification_manifest_metadata():
    """Verify VerificationPlugin manifest contains required attributes and 10 capabilities."""
    manifest = VERIFICATION_PLUGIN_MANIFEST
    assert manifest.name == "verification"
    assert manifest.version == "0.1.0"
    assert "quality" in manifest.description.lower() or "verification" in manifest.description.lower()

    # Verify all 10 capabilities are present
    assert PluginCapability.OUTPUT_VALIDATION.value in manifest.capabilities
    assert PluginCapability.FACT_CHECKING.value in manifest.capabilities
    assert PluginCapability.RESULT_RERANKING.value in manifest.capabilities
    assert PluginCapability.CONSISTENCY_CHECKING.value in manifest.capabilities
    assert PluginCapability.CODE_VERIFICATION.value in manifest.capabilities
    assert PluginCapability.DATA_VERIFICATION.value in manifest.capabilities
    assert PluginCapability.SOURCE_EVIDENCE_CHECK.value in manifest.capabilities
    assert PluginCapability.CONFIDENCE_SCORING.value in manifest.capabilities
    assert PluginCapability.LLM_JUDGE.value in manifest.capabilities
    assert PluginCapability.FINAL_RESPONSE_VERIFICATION.value in manifest.capabilities

    assert len(manifest.capabilities) == 10
    assert manifest.input_schema_name == "VerificationInput"
    assert manifest.output_schema_name == "VerificationResult"


def test_verification_plugin_contract_properties():
    """Verify VerificationPlugin conforms to BasePlugin abstract contract."""
    plugin = VerificationPlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "verification"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) == 10
    assert plugin.input_schema is VerificationInput
    assert plugin.output_schema is VerificationResult


def test_verification_plugin_lifecycle():
    """Verify initialize and shutdown hooks update readiness state."""
    plugin = VerificationPlugin()
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_verification_plugin_health_check():
    """Verify synchronous and asynchronous health check reporting."""
    plugin = VerificationPlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["initialized"] is True
    assert health.details["tools_ready"] is True
    assert health.error is None
    assert health.latency_ms >= 0.0

    # health alias
    assert plugin.health().status == PluginHealthStatus.HEALTHY

    # Shut down plugin -> unhealthy
    plugin.shutdown()
    unhealthy = plugin.health_check()
    assert unhealthy.status == PluginHealthStatus.UNHEALTHY
    assert unhealthy.error is not None


@pytest.mark.asyncio
async def test_verification_plugin_ahealth_check():
    """Verify asynchronous health check."""
    plugin = VerificationPlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["initialized"] is True


def test_verification_plugin_registration_in_plugin_manager():
    """Verify VerificationPlugin can be registered, listed, and queried in PluginManager."""
    manager = PluginManager()
    plugin = VerificationPlugin()
    manager.register(plugin)

    assert manager.has("verification")
    assert manager.get("verification") is plugin

    manifests = manager.list_plugins()
    assert any(m.name == "verification" for m in manifests)

    # Capability queries
    for cap in [
        PluginCapability.OUTPUT_VALIDATION,
        PluginCapability.FACT_CHECKING,
        PluginCapability.RESULT_RERANKING,
        PluginCapability.CONSISTENCY_CHECKING,
        PluginCapability.CODE_VERIFICATION,
        PluginCapability.DATA_VERIFICATION,
        PluginCapability.SOURCE_EVIDENCE_CHECK,
        PluginCapability.CONFIDENCE_SCORING,
        PluginCapability.LLM_JUDGE,
        PluginCapability.FINAL_RESPONSE_VERIFICATION,
    ]:
        plugins_with_cap = manager.list_by_capability(cap)
        assert any(p.name == "verification" for p in plugins_with_cap)
