"""Unit tests for MockLLM provider."""

import pytest
from pydantic import BaseModel, Field

from xeren.models.errors import OutputParsingError, RateLimitError
from xeren.models.providers.mock import MockLLM
from xeren.models.types import ChatMessage


class SentimentAnalysis(BaseModel):
    sentiment: str
    confidence: float = Field(ge=0.0, le=1.0)


def test_mock_sync_generate() -> None:
    llm = MockLLM(canned_response="Hello world!")
    messages = [ChatMessage.user("Hi")]
    resp = llm.generate(messages)

    assert resp.content == "Hello world!"
    assert resp.message.content == "Hello world!"
    assert resp.finish_reason == "stop"
    assert resp.usage.total_tokens > 0
    assert len(llm.call_history) == 1


@pytest.mark.asyncio
async def test_mock_async_generate() -> None:
    llm = MockLLM(canned_response="Async reply")
    messages = [ChatMessage.user("Test")]
    resp = await llm.agenerate(messages)

    assert resp.content == "Async reply"
    assert resp.finish_reason == "stop"


def test_mock_stream() -> None:
    llm = MockLLM(stream_chunks=["Hello", " ", "World", "!"])
    messages = [ChatMessage.user("Stream test")]
    chunks = list(llm.stream(messages))

    assert len(chunks) == 5  # 4 tokens + 1 final stop chunk
    joined_text = "".join(c.delta_content for c in chunks)
    assert joined_text == "Hello World!"
    assert chunks[-1].finish_reason == "stop"


@pytest.mark.asyncio
async def test_mock_astream() -> None:
    llm = MockLLM(stream_chunks=["Async", " ", "Stream"])
    messages = [ChatMessage.user("Async stream test")]
    chunks = []
    async for c in llm.astream(messages):
        chunks.append(c)

    joined_text = "".join(c.delta_content for c in chunks)
    assert joined_text == "Async Stream"


def test_mock_structured_output_success() -> None:
    valid_json = '{"sentiment": "positive", "confidence": 0.95}'
    llm = MockLLM(canned_response=valid_json)
    messages = [ChatMessage.user("Analyze: 'I love this product'")]

    result = llm.generate_structured(messages, schema=SentimentAnalysis)
    assert isinstance(result, SentimentAnalysis)
    assert result.sentiment == "positive"
    assert result.confidence == 0.95


def test_mock_structured_output_markdown_wrapped() -> None:
    wrapped_json = '```json\n{"sentiment": "negative", "confidence": 0.88}\n```'
    llm = MockLLM(canned_response=wrapped_json)
    messages = [ChatMessage.user("Analyze: 'Bad experience'")]

    result = llm.generate_structured(messages, schema=SentimentAnalysis)
    assert result.sentiment == "negative"
    assert result.confidence == 0.88


def test_mock_structured_output_failure() -> None:
    invalid_json = 'This is not valid json at all'
    llm = MockLLM(canned_response=invalid_json)
    messages = [ChatMessage.user("Analyze")]

    with pytest.raises(OutputParsingError) as exc_info:
        llm.generate_structured(messages, schema=SentimentAnalysis)
    assert "Failed to parse LLM response" in str(exc_info.value)
    assert exc_info.value.raw_output == invalid_json


def test_mock_simulated_error() -> None:
    llm = MockLLM(error_to_raise=RateLimitError("Rate limit reached"))
    messages = [ChatMessage.user("Hello")]

    with pytest.raises(RateLimitError):
        llm.generate(messages)
