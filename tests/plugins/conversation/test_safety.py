"""Tests for safe failure handling, empty input, provider failure, timeouts, and CoT suppression."""

import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.contract import PluginExecutionContext
from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.provider import (
    DeterministicConversationProvider,
    LLMConversationProvider,
)
from xeren.plugins.conversation.schemas import (
    ConversationInput,
    ConversationIntent,
    ConversationResult,
)
from xeren.plugins.errors import PluginValidationError


def test_empty_string_input_safely_handled() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": ""})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.CLARIFICATION
    assert output.clarification_needed is True
    assert "empty" in output.response.lower()


def test_whitespace_only_input_safely_handled() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": "     \n\t   "})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.CLARIFICATION
    assert output.clarification_needed is True


def test_malformed_input_raises_validation_error() -> None:
    plugin = ConversationPlugin()
    # Missing required message field
    with pytest.raises(PluginValidationError):
        plugin.execute({"tone": "friendly"})

    # Non-dictionary / non-model payload
    with pytest.raises(PluginValidationError):
        plugin.execute(12345)  # type: ignore


def test_provider_failure_with_safe_fallback() -> None:
    # Injected provider that raises an exception
    failing_provider = DeterministicConversationProvider(
        error_to_raise=RuntimeError("Simulated provider connection failure")
    )
    plugin = ConversationPlugin(provider=failing_provider, safe_fallback_on_error=True)

    res = plugin.execute({"message": "Hello"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.UNKNOWN
    assert "unexpected issue" in output.response.lower()
    assert res.metadata.get("recovered_from_error") is True


def test_timeout_handling() -> None:
    slow_provider = DeterministicConversationProvider(latency_seconds=0.3)
    plugin = ConversationPlugin(provider=slow_provider, safe_fallback_on_error=True)

    ctx = PluginExecutionContext(timeout_seconds=0.05)
    res = plugin.execute({"message": "Hello"}, context=ctx)
    assert res.success is False
    assert "timed out" in (res.error or "").lower()


def test_zero_chain_of_thought_leakage() -> None:
    # Create an LLM that returns hidden thinking tags
    mock_llm = MockLLM(
        canned_response="<thought>The user is greeting me. I should respond politely.</thought>Hello! How can I help you today?"
    )
    provider = LLMConversationProvider(llm=mock_llm)
    plugin = ConversationPlugin(provider=provider)

    res = plugin.execute({"message": "Hello"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output

    assert "<thought>" not in output.response
    assert "</thought>" not in output.response
    assert "The user is greeting me" not in output.response
    assert output.response == "Hello! How can I help you today?"


def test_zero_chain_of_thought_header_leakage() -> None:
    mock_llm = MockLLM(
        canned_response="Chain of thought: internal reasoning steps here.\n\nGood day! How can I assist you?"
    )
    provider = LLMConversationProvider(llm=mock_llm)
    plugin = ConversationPlugin(provider=provider)

    res = plugin.execute({"message": "Hello"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output

    assert "Chain of thought" not in output.response
    assert output.response == "Good day! How can I assist you?"
