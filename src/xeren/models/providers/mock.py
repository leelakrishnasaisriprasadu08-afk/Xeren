"""In-memory Mock LLM provider for deterministic testing."""

import asyncio
from typing import Any, AsyncIterator, Iterator, List, Optional

from xeren.models.base import BaseLLM
from xeren.models.config import ModelConfig
from xeren.models.types import ChatMessage, LLMResponse, Role, StreamChunk, TokenUsage


class MockLLM(BaseLLM):
    """Mock LLM adapter for testing without external API calls or network dependencies."""

    def __init__(
        self,
        config: Optional[ModelConfig] = None,
        canned_response: Optional[str] = None,
        stream_chunks: Optional[List[str]] = None,
        error_to_raise: Optional[Exception] = None,
        latency_seconds: float = 0.0,
    ) -> None:
        cfg = config or ModelConfig(model_id="mock-model", provider="mock")
        super().__init__(cfg)
        self.canned_response = canned_response
        self.stream_chunks = stream_chunks
        self.error_to_raise = error_to_raise
        self.latency_seconds = latency_seconds
        self.call_history: List[List[ChatMessage]] = []

    def _get_reply_text(self, messages: List[ChatMessage]) -> str:
        if self.canned_response is not None:
            return self.canned_response
        if messages and messages[-1].content:
            return f"Mock response to: {messages[-1].content}"
        return "Mock default response"

    def generate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_history.append(messages)
        if self.error_to_raise:
            raise self.error_to_raise

        active_config = self._resolve_config(config)
        content = self._get_reply_text(messages)
        prompt_chars = sum(len(m.content or "") for m in messages)

        return LLMResponse(
            content=content,
            message=ChatMessage(role=Role.ASSISTANT, content=content),
            finish_reason="stop",
            usage=TokenUsage(
                prompt_tokens=max(1, prompt_chars // 4),
                completion_tokens=max(1, len(content) // 4),
                total_tokens=max(2, (prompt_chars + len(content)) // 4),
            ),
            model_id=active_config.model_id,
            raw_response={"mock": True},
        )

    async def agenerate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)
        return self.generate(messages, config=config, **kwargs)

    def stream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> Iterator[StreamChunk]:
        self.call_history.append(messages)
        if self.error_to_raise:
            raise self.error_to_raise

        chunks = self.stream_chunks or [self._get_reply_text(messages)]
        for chunk in chunks:
            yield StreamChunk(delta_content=chunk)
        yield StreamChunk(delta_content="", finish_reason="stop")

    async def astream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        self.call_history.append(messages)
        if self.error_to_raise:
            raise self.error_to_raise

        chunks = self.stream_chunks or [self._get_reply_text(messages)]
        for chunk in chunks:
            if self.latency_seconds > 0:
                await asyncio.sleep(self.latency_seconds)
            yield StreamChunk(delta_content=chunk)
        yield StreamChunk(delta_content="", finish_reason="stop")
