"""Xeren Conversation Plugin for natural everyday interaction with Xeren."""

from xeren.plugins.conversation.manifest import CONVERSATION_PLUGIN_MANIFEST
from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.provider import (
    ConversationProvider,
    DeterministicConversationProvider,
    LLMConversationProvider,
)
from xeren.plugins.conversation.schemas import (
    ConversationInput,
    ConversationIntent,
    ConversationMessage,
    ConversationResult,
    ConversationTone,
    RoutingSignal,
)

__all__ = [
    "CONVERSATION_PLUGIN_MANIFEST",
    "ConversationPlugin",
    "ConversationProvider",
    "DeterministicConversationProvider",
    "LLMConversationProvider",
    "ConversationInput",
    "ConversationResult",
    "ConversationIntent",
    "ConversationTone",
    "ConversationMessage",
    "RoutingSignal",
]
