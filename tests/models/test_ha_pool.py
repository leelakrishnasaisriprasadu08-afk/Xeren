"""Tests for HighAvailabilityModelPool with automatic multi-provider cascade failover."""

import asyncio
from typing import Any, AsyncIterator, Iterator, List, Optional
import pytest

from xeren.models.base import BaseLLM
from xeren.models.config import ModelConfig
from xeren.models.errors import ProviderConnectionError, RateLimitError
from xeren.models.pool import HighAvailabilityModelPool, ProviderLane
from xeren.models.types import ChatMessage, LLMResponse, StreamChunk


class FlakyMockLLM(BaseLLM):
    """Mock LLM that can be configured to fail or succeed."""

    def __init__(self, name: str, should_fail: bool = False, fail_error: Exception = None):
        super().__init__(config=ModelConfig(model_id=name, provider="mock"))
        self.name = name
        self.should_fail = should_fail
        self.fail_error = fail_error or RateLimitError("Rate limit 429 exceeded on upstream")

    def generate(self, messages: List[ChatMessage], config: Optional[ModelConfig] = None, **kwargs: Any) -> LLMResponse:
        if self.should_fail:
            raise self.fail_error
        text = f"Success from {self.name}"
        return LLMResponse(content=text, message=ChatMessage.assistant(text), raw_response={})

    async def agenerate(self, messages: List[ChatMessage], config: Optional[ModelConfig] = None, **kwargs: Any) -> LLMResponse:
        if self.should_fail:
            raise self.fail_error
        text = f"Async success from {self.name}"
        return LLMResponse(content=text, message=ChatMessage.assistant(text), raw_response={})

    def stream(self, messages: List[ChatMessage], config: Optional[ModelConfig] = None, **kwargs: Any) -> Iterator[StreamChunk]:
        if self.should_fail:
            raise self.fail_error
        yield StreamChunk(delta_content=f"Stream from {self.name}", finish_reason="stop")

    async def astream(self, messages: List[ChatMessage], config: Optional[ModelConfig] = None, **kwargs: Any) -> AsyncIterator[StreamChunk]:
        if self.should_fail:
            raise self.fail_error
        yield StreamChunk(delta_content=f"Async stream from {self.name}", finish_reason="stop")


def test_primary_lane_success():
    """Verify primary lane handles requests when healthy."""
    lane1 = ProviderLane("groq_primary", FlakyMockLLM("groq", should_fail=False), priority=1)
    lane2 = ProviderLane("gemini_backup", FlakyMockLLM("gemini", should_fail=False), priority=2)
    pool = HighAvailabilityModelPool(lanes=[lane1, lane2])

    resp = pool.generate([ChatMessage.user("hello")])
    assert "Success from groq" in resp.content
    assert lane1.total_successes == 1
    assert lane2.total_requests == 0


def test_cascade_failover_on_rate_limit():
    """Verify that when primary hits 429 RateLimit, pool seamlessly cascades to backup lane."""
    lane1 = ProviderLane("groq_primary", FlakyMockLLM("groq", should_fail=True), priority=1)
    lane2 = ProviderLane("gemini_backup", FlakyMockLLM("gemini", should_fail=False), priority=2)
    pool = HighAvailabilityModelPool(lanes=[lane1, lane2])

    # Should not raise; fails over silently to lane 2
    resp = pool.generate([ChatMessage.user("ping")])
    assert "Success from gemini" in resp.content
    assert lane1.consecutive_failures == 1
    assert lane2.total_successes == 1


@pytest.mark.asyncio
async def test_async_cascade_failover():
    """Verify async generation cascades without breaking."""
    lane1 = ProviderLane("lane1", FlakyMockLLM("m1", should_fail=True), priority=1)
    lane2 = ProviderLane("lane2", FlakyMockLLM("m2", should_fail=False), priority=2)
    pool = HighAvailabilityModelPool(lanes=[lane1, lane2])

    resp = await pool.agenerate([ChatMessage.user("async test")])
    assert "Async success from m2" in resp.content


@pytest.mark.asyncio
async def test_astream_cascade_failover():
    """Verify streaming fails over cleanly before tokens start."""
    lane1 = ProviderLane("lane1", FlakyMockLLM("m1", should_fail=True), priority=1)
    lane2 = ProviderLane("lane2", FlakyMockLLM("m2", should_fail=False), priority=2)
    pool = HighAvailabilityModelPool(lanes=[lane1, lane2])

    chunks = []
    async for chunk in pool.astream([ChatMessage.user("stream test")]):
        chunks.append(chunk.delta_content)

    full = "".join(chunks)
    assert "Async stream from m2" in full


def test_all_lanes_exhausted_raises_safe_error():
    """Verify pool raises ProviderConnectionError when all lanes fail, instead of unhandled crash."""
    lane1 = ProviderLane("lane1", FlakyMockLLM("m1", should_fail=True), priority=1)
    lane2 = ProviderLane("lane2", FlakyMockLLM("m2", should_fail=True), priority=2)
    pool = HighAvailabilityModelPool(lanes=[lane1, lane2])

    with pytest.raises(ProviderConnectionError) as exc_info:
        pool.generate([ChatMessage.user("fail test")])

    assert "All 2 provider lanes in HA pool exhausted" in str(exc_info.value)


def test_circuit_breaker_tripping_and_telemetry():
    """Verify circuit breaker opens after consecutive failures and reflects in telemetry."""
    llm1 = FlakyMockLLM("m1", should_fail=True)
    lane1 = ProviderLane("lane1", llm1, priority=1, max_consecutive_failures=2, cooldown_seconds=60.0)
    llm2 = FlakyMockLLM("m2", should_fail=False)
    lane2 = ProviderLane("lane2", llm2, priority=2)
    pool = HighAvailabilityModelPool(lanes=[lane1, lane2])

    # First request: lane1 fails (1), cascades to lane2
    pool.generate([ChatMessage.user("req 1")])
    assert lane1.consecutive_failures == 1
    assert lane1.is_available is True

    # Second request: lane1 fails (2 >= max), circuit trips!
    pool.generate([ChatMessage.user("req 2")])
    assert lane1.consecutive_failures == 2
    assert lane1.is_available is False  # circuit open

    # Third request: lane1 is in cooldown, pool goes directly to lane2 without attempting lane1!
    pool.generate([ChatMessage.user("req 3")])
    assert lane1.total_requests == 2  # was not even called on 3rd request!

    # Telemetry verification
    status = pool.get_pool_status()
    assert status["total_lanes"] == 2
    assert status["healthy_lanes"] == 1
    assert status["lanes"][0]["available"] is False
    assert status["lanes"][1]["available"] is True
