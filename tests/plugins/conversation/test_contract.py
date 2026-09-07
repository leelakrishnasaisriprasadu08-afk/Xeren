"""Contract tests for ConversationPlugin conforming to BasePlugin."""

from xeren.plugins.contract import BasePlugin, PluginHealthStatus
from xeren.plugins.conversation.manifest import CONVERSATION_PLUGIN_MANIFEST
from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.schemas import ConversationInput, ConversationResult
from xeren.plugins.manager import PluginManager


def test_manifest_metadata() -> None:
    manifest = CONVERSATION_PLUGIN_MANIFEST
    assert manifest.name == "conversation"
    assert manifest.version == "0.1.0"
    assert "conversation" in manifest.capabilities
    assert "greeting" in manifest.capabilities
    assert "routing_signal" in manifest.capabilities
    assert manifest.input_schema_name == "ConversationInput"
    assert manifest.output_schema_name == "ConversationResult"


def test_plugin_conformance_and_properties() -> None:
    plugin = ConversationPlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "conversation"
    assert plugin.version == "0.1.0"
    assert plugin.input_schema == ConversationInput
    assert plugin.output_schema == ConversationResult


def test_plugin_registration_with_manager() -> None:
    manager = PluginManager()
    plugin = ConversationPlugin()
    manager.register(plugin)

    assert manager.has("conversation") is True
    retrieved = manager.get("conversation")
    assert retrieved is plugin

    names = manager.list_names()
    assert "conversation" in names

    manifests = manager.list_plugins()
    assert any(m.name == "conversation" for m in manifests)


def test_health_check() -> None:
    plugin = ConversationPlugin()
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details.get("name") == "conversation"
    assert health.latency_ms >= 0.0
