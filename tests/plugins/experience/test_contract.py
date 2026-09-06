"""Tests for ExperiencePlugin contract, manifest, capabilities, and lifecycle."""

import pytest

from xeren.plugins.contract import BasePlugin, PluginCapability, PluginHealthStatus
from xeren.plugins.experience.manifest import EXPERIENCE_PLUGIN_MANIFEST
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.experience.schemas import ExperienceInput, ExperienceResult
from xeren.plugins.manager import PluginManager


def test_experience_manifest_metadata():
    """Verify ExperiencePlugin manifest contains required attributes and 10 capabilities."""
    manifest = EXPERIENCE_PLUGIN_MANIFEST
    assert manifest.name == "experience"
    assert manifest.version == "0.1.0"
    assert "experience" in manifest.description.lower() or "feedback" in manifest.description.lower()

    # All 10 capabilities
    assert PluginCapability.EXPERIENCE_RECORD.value in manifest.capabilities
    assert PluginCapability.EXPERIENCE_RETRIEVAL.value in manifest.capabilities
    assert PluginCapability.SUCCESS_HISTORY.value in manifest.capabilities
    assert PluginCapability.FAILURE_HISTORY.value in manifest.capabilities
    assert PluginCapability.USER_FEEDBACK.value in manifest.capabilities
    assert PluginCapability.PATTERN_DETECTION.value in manifest.capabilities
    assert PluginCapability.LESSON_EXTRACTION.value in manifest.capabilities
    assert PluginCapability.EXPERIENCE_RANKING.value in manifest.capabilities
    assert PluginCapability.FAILURE_AVOIDANCE.value in manifest.capabilities
    assert PluginCapability.OUTCOME_TRACKING.value in manifest.capabilities

    assert len(manifest.capabilities) == 10
    assert manifest.input_schema_name == "ExperienceInput"
    assert manifest.output_schema_name == "ExperienceResult"
    assert manifest.metadata.get("self_training") is False


def test_experience_plugin_contract_properties():
    """Verify ExperiencePlugin conforms to BasePlugin abstract contract."""
    plugin = ExperiencePlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "experience"
    assert plugin.version == "0.1.0"
    assert len(plugin.capabilities) == 10
    assert plugin.input_schema is ExperienceInput
    assert plugin.output_schema is ExperienceResult


def test_experience_plugin_lifecycle():
    """Verify initialize and shutdown hooks update operational readiness."""
    plugin = ExperiencePlugin()
    assert plugin._initialized is True
    plugin.shutdown()
    assert plugin._initialized is False
    plugin.initialize()
    assert plugin._initialized is True


def test_experience_plugin_health_check():
    """Verify synchronous and asynchronous health check reporting."""
    plugin = ExperiencePlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["initialized"] is True
    assert health.details["tools_ready"] is True
    assert health.details["store_type"] == "InMemoryExperienceStore"
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
async def test_experience_plugin_ahealth_check():
    """Verify asynchronous health check."""
    plugin = ExperiencePlugin()
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["initialized"] is True


def test_experience_plugin_registration_in_plugin_manager():
    """Verify ExperiencePlugin can be registered, listed, and queried in PluginManager."""
    manager = PluginManager()
    plugin = ExperiencePlugin()
    manager.register(plugin)

    assert manager.has("experience")
    assert manager.get("experience") is plugin

    manifests = manager.list_plugins()
    assert any(m.name == "experience" for m in manifests)

    # Capability queries
    for cap in [
        PluginCapability.EXPERIENCE_RECORD,
        PluginCapability.EXPERIENCE_RETRIEVAL,
        PluginCapability.SUCCESS_HISTORY,
        PluginCapability.FAILURE_HISTORY,
        PluginCapability.USER_FEEDBACK,
        PluginCapability.PATTERN_DETECTION,
        PluginCapability.LESSON_EXTRACTION,
        PluginCapability.EXPERIENCE_RANKING,
        PluginCapability.FAILURE_AVOIDANCE,
        PluginCapability.OUTCOME_TRACKING,
    ]:
        plugins_with_cap = manager.list_by_capability(cap)
        assert any(p.name == "experience" for p in plugins_with_cap)
