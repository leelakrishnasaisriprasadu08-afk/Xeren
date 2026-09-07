"""Manifest definition for the Xeren Conversation Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

CONVERSATION_PLUGIN_MANIFEST = PluginManifest(
    name="conversation",
    version="0.1.0",
    description="Lightweight conversational layer for natural everyday interaction with Xeren, handling greetings, casual chat, pleasantries, simple explanations, conversational follow-ups, and tool routing signals.",
    capabilities=[
        PluginCapability.CUSTOM.value,
        "conversation",
        "greeting",
        "casual_chat",
        "explanation",
        "clarification",
        "routing_signal",
    ],
    input_schema_name="ConversationInput",
    output_schema_name="ConversationResult",
    author="Xeren Core Team",
    metadata={
        "category": "conversational_interface",
        "supports_async": True,
        "supports_context": True,
        "injectable_provider": True,
        "deterministic_fallback": True,
    },
)

__all__ = ["CONVERSATION_PLUGIN_MANIFEST"]
