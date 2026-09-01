"""Unit tests for chat message types, usage accounting, and response schemas."""

from xeren.models.types import (
    ChatMessage,
    FunctionCall,
    LLMResponse,
    Role,
    StreamChunk,
    TokenUsage,
    ToolCall,
)


def test_chat_message_factories() -> None:
    sys_msg = ChatMessage.system("You are an assistant.")
    assert sys_msg.role == Role.SYSTEM
    assert sys_msg.content == "You are an assistant."

    user_msg = ChatMessage.user("Hello world")
    assert user_msg.role == Role.USER
    assert user_msg.content == "Hello world"

    tc = ToolCall(
        id="call_123",
        function=FunctionCall(name="get_weather", arguments='{"city": "Paris"}'),
    )
    asst_msg = ChatMessage.assistant(content="Checking weather...", tool_calls=[tc])
    assert asst_msg.role == Role.ASSISTANT
    assert asst_msg.content == "Checking weather..."
    assert asst_msg.tool_calls is not None
    assert len(asst_msg.tool_calls) == 1
    assert asst_msg.tool_calls[0].function.name == "get_weather"

    tool_msg = ChatMessage.tool(content='{"temp": "22C"}', tool_call_id="call_123")
    assert tool_msg.role == Role.TOOL
    assert tool_msg.content == '{"temp": "22C"}'
    assert tool_msg.tool_call_id == "call_123"


def test_token_usage_model() -> None:
    usage = TokenUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75, estimated_cost=0.0015)
    assert usage.prompt_tokens == 50
    assert usage.completion_tokens == 25
    assert usage.total_tokens == 75
    assert usage.estimated_cost == 0.0015


def test_llm_response_model() -> None:
    msg = ChatMessage.assistant("Test reply")
    resp = LLMResponse(
        content="Test reply",
        message=msg,
        finish_reason="stop",
        model_id="test-model",
    )
    assert resp.content == "Test reply"
    assert resp.message.role == Role.ASSISTANT
    assert resp.finish_reason == "stop"
    assert resp.model_id == "test-model"


def test_stream_chunk_model() -> None:
    chunk = StreamChunk(delta_content="token", finish_reason=None)
    assert chunk.delta_content == "token"
    assert chunk.finish_reason is None
