"""Tests for dependency injection and provider swappability."""

from xeren.models.providers.mock import MockLLM
from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.provider import (
    ConversationProvider,
    DeterministicConversationProvider,
    LLMConversationProvider,
)
from xeren.plugins.conversation.schemas import (
    ConversationInput,
    ConversationIntent,
    ConversationResult,
    ConversationTone,
)


class CustomTestProvider(ConversationProvider):
    """Custom injected provider for testing dependency injection."""

    def generate_response(self, input_data: ConversationInput) -> ConversationResult:
        return ConversationResult(
            response=f"Custom: {input_data.message}",
            intent=ConversationIntent.CASUAL,
            tone_used=input_data.tone,
            metadata={"custom_flag": True},
        )


def test_deterministic_provider_canned_override() -> None:
    det_provider = DeterministicConversationProvider()
    det_provider.set_canned_response("ping", "pong")
    plugin = ConversationPlugin(provider=det_provider)

    res = plugin.execute({"message": "ping"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.response == "pong"


def test_custom_provider_injection() -> None:
    custom_prov = CustomTestProvider()
    plugin = ConversationPlugin(provider=custom_prov)

    res = plugin.execute({"message": "Testing custom provider"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.response == "Custom: Testing custom provider"
    assert output.metadata.get("custom_flag") is True


def test_dynamic_set_provider() -> None:
    plugin = ConversationPlugin()
    assert isinstance(plugin.provider, DeterministicConversationProvider)

    plugin.set_provider(CustomTestProvider())
    assert isinstance(plugin.provider, CustomTestProvider)

    res = plugin.execute({"message": "Dynamic swap"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.response == "Custom: Dynamic swap"


def test_llm_provider_injection_and_set_llm() -> None:
    mock_llm = MockLLM(canned_response="Hello from injected mock LLM!")
    plugin = ConversationPlugin(llm=mock_llm)
    assert isinstance(plugin.provider, LLMConversationProvider)

    res = plugin.execute({"message": "Hello"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.response == "Hello from injected mock LLM!"

    # Test set_llm
    new_mock_llm = MockLLM(canned_response="Updated mock LLM response!")
    plugin.set_llm(new_mock_llm)

    res2 = plugin.execute({"message": "Hello again"})
    assert res2.success is True
    assert isinstance(res2.output, ConversationResult)
    output2 = res2.output
    assert output2.response == "Updated mock LLM response!"
