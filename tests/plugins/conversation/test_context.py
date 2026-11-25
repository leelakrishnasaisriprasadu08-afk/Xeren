"""Tests for multi-turn conversation context preservation and follow-up handling."""

from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.schemas import (
    ConversationInput,
    ConversationIntent,
    ConversationMessage,
    ConversationResult,
)


def test_followup_with_context() -> None:
    plugin = ConversationPlugin()

    history = [
        ConversationMessage(role="user", content="Can you explain recursion?"),
        ConversationMessage(
            role="assistant",
            content="Recursion is a technique where a function solves a problem by calling itself with smaller sub-problems until reaching a base case.",
        ),
    ]

    payload = ConversationInput(
        message="Can you tell me more about that?",
        context=history,
    )

    res = plugin.execute(payload)
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.FOLLOW_UP
    assert output.context_preserved is True
    assert output.clarification_needed is False
    assert "recursion" in output.response.lower() or "base case" in output.response.lower() or "sub-problems" in output.response.lower()


def test_followup_without_context_requests_clarification() -> None:
    plugin = ConversationPlugin()

    payload = ConversationInput(
        message="Tell me more about that",
        context=[],  # empty context!
    )

    res = plugin.execute(payload)
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.FOLLOW_UP
    assert output.context_preserved is False
    assert output.clarification_needed is True
    assert "clarify" in output.response.lower() or "expand" in output.response.lower()


def test_short_why_with_context() -> None:
    plugin = ConversationPlugin()

    history = [
        ConversationMessage(role="user", content="Why use Python for AI?"),
        ConversationMessage(
            role="assistant",
            content="Python provides extensive libraries like PyTorch and NumPy for matrix computation and neural networks.",
        ),
    ]

    payload = ConversationInput(
        message="And why is that important?",
        context=history,
    )

    res = plugin.execute(payload)
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.FOLLOW_UP
    assert output.context_preserved is True
