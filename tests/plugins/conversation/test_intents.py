"""Tests for conversational intent classification and response generation."""

import pytest

from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.schemas import (
    ConversationInput,
    ConversationIntent,
    ConversationResult,
    ConversationTone,
)


@pytest.fixture
def plugin() -> ConversationPlugin:
    return ConversationPlugin()


def test_greeting_friendly(plugin: ConversationPlugin) -> None:
    res = plugin.execute({"message": "Hello Xeren!", "tone": "friendly"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.GREETING
    assert "hello" in output.response.lower() or "great to connect" in output.response.lower()
    assert output.routing.requires_tool is False


def test_greeting_personalized_and_professional(plugin: ConversationPlugin) -> None:
    payload = ConversationInput(
        message="Good morning",
        user_name="Alice",
        tone=ConversationTone.PROFESSIONAL,
    )
    res = plugin.execute(payload)
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.GREETING
    assert "Alice" in output.response
    assert "assistance" in output.response.lower() or "good day" in output.response.lower()


def test_greeting_concise_tone(plugin: ConversationPlugin) -> None:
    res = plugin.execute({"message": "Hi", "tone": "concise"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.GREETING
    assert len(output.response.split()) <= 10


def test_casual_conversation(plugin: ConversationPlugin) -> None:
    for query in ["How are you doing today?", "How's your day going?", "What can you do?"]:
        res = plugin.execute({"message": query})
        assert res.success is True
        assert isinstance(res.output, ConversationResult)
        output = res.output
        assert output.intent == ConversationIntent.CASUAL
        assert output.response
        assert output.routing.requires_tool is False


def test_thanks(plugin: ConversationPlugin) -> None:
    for thanks_phrase in ["Thank you!", "Thanks so much for the help", "Appreciate it!"]:
        res = plugin.execute({"message": thanks_phrase})
        assert res.success is True
        assert isinstance(res.output, ConversationResult)
        output = res.output
        assert output.intent == ConversationIntent.THANKS
        assert "welcome" in output.response.lower() or "pleasure" in output.response.lower()


def test_goodbye(plugin: ConversationPlugin) -> None:
    for bye_phrase in ["Goodbye!", "See you later", "Farewell", "Have a great day"]:
        res = plugin.execute({"message": bye_phrase})
        assert res.success is True
        assert isinstance(res.output, ConversationResult)
        output = res.output
        assert output.intent == ConversationIntent.GOODBYE
        assert "goodbye" in output.response.lower() or "day" in output.response.lower() or "farewell" in output.response.lower()


def test_simple_explanation_neural_network(plugin: ConversationPlugin) -> None:
    res = plugin.execute({"message": "What is a neural network?", "tone": "friendly"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.EXPLANATION
    assert "neural" in output.response.lower() or "machine learning" in output.response.lower()
    assert output.routing.requires_tool is False


def test_simple_explanation_api(plugin: ConversationPlugin) -> None:
    res = plugin.execute({"message": "What does API stand for?", "tone": "informative"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.EXPLANATION
    assert "application programming interface" in output.response.lower()


def test_clarification_request(plugin: ConversationPlugin) -> None:
    res = plugin.execute({"message": "Could you clarify what you mean?"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.CLARIFICATION
    assert output.clarification_needed is True
    assert "detail" in output.response.lower() or "clarify" in output.response.lower()
