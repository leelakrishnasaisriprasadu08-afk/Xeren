"""Integration tests between XerenCore and the ConversationPlugin."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.models.providers.mock import MockLLM
from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.schemas import ConversationIntent, ConversationResult


def test_core_initialization_auto_registers_conversation_plugin() -> None:
    core = XerenCore()
    assert core.has_plugin("conversation") is True
    manifests = core.list_plugins()
    assert any(m.name == "conversation" for m in manifests)


def test_core_execute_conversation_plugin() -> None:
    core = XerenCore()
    exec_res = core.execute_plugin("conversation", {"message": "Hello Xeren, good morning!"})

    assert exec_res.success is True
    assert exec_res.plugin_name == "conversation"
    assert isinstance(exec_res.output, ConversationResult)
    assert exec_res.output.intent == ConversationIntent.GREETING
    assert exec_res.output.routing.requires_tool is False


def test_core_execute_conversation_tool_routing() -> None:
    core = XerenCore()
    exec_res = core.execute_plugin(
        "conversation",
        {"message": "Please search the web for recent Python releases"},
    )

    assert exec_res.success is True
    assert isinstance(exec_res.output, ConversationResult)
    output = exec_res.output
    assert output.intent == ConversationIntent.TOOL_REQUIRED
    assert output.routing.requires_tool is True
    assert output.routing.suggested_plugin == "research"


def test_core_set_llm_updates_conversation_plugin() -> None:
    core = XerenCore()
    mock_llm = MockLLM(canned_response="Custom core LLM conversation response.")
    core.set_llm(mock_llm)

    exec_res = core.execute_plugin("conversation", {"message": "Tell me a joke"})
    assert exec_res.success is True
    assert isinstance(exec_res.output, ConversationResult)
    output = exec_res.output
    assert output.response == "Custom core LLM conversation response."
