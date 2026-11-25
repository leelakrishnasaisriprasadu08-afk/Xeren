"""Unit and integration tests for LocalOpenWeightAdapter using httpx transport mocking."""

import json
import httpx
import pytest
from pydantic import BaseModel

from xeren.models.config import LocalModelConfig
from xeren.models.errors import (
    AuthenticationError,
    ContextLengthExceededError,
    InferenceTimeoutError,
    ModelNotFoundError,
    OutputParsingError,
    ProviderConnectionError,
    RateLimitError,
)
from xeren.models.providers.local_openweight import LocalOpenWeightAdapter
from xeren.models.types import ChatMessage, Role


class CodeReviewResult(BaseModel):
    has_bugs: bool
    summary: str


@pytest.fixture
def base_config() -> LocalModelConfig:
    return LocalModelConfig(
        model_id="llama3.2:3b",
        api_base="http://localhost:11434/v1",
        temperature=0.1,
    )


def test_local_generate_sync(base_config: LocalModelConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        req_data = json.loads(request.read())
        assert req_data["model"] == "llama3.2:3b"
        assert req_data["temperature"] == 0.1
        assert req_data["stream"] is False
        assert len(req_data["messages"]) == 1
        assert req_data["messages"][0]["content"] == "Write a hello world"

        resp_payload = {
            "id": "chatcmpl-123",
            "model": "llama3.2:3b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "print('Hello, world!')",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18,
            },
        }
        return httpx.Response(200, json=resp_payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    messages = [ChatMessage.user("Write a hello world")]
    response = adapter.generate(messages)

    assert response.content == "print('Hello, world!')"
    assert response.message.role == Role.ASSISTANT
    assert response.finish_reason == "stop"
    assert response.usage.prompt_tokens == 10
    assert response.usage.completion_tokens == 8
    assert response.usage.total_tokens == 18
    assert response.model_id == "llama3.2:3b"


@pytest.mark.asyncio
async def test_local_agenerate_async(base_config: LocalModelConfig) -> None:
    async def ahandler(request: httpx.Request) -> httpx.Response:
        resp_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Async response text",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
        }
        return httpx.Response(200, json=resp_payload)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(ahandler))
    adapter = LocalOpenWeightAdapter(base_config, async_client=async_client)

    messages = [ChatMessage.user("Async query")]
    response = await adapter.agenerate(messages)

    assert response.content == "Async response text"
    assert response.usage.total_tokens == 10


def test_local_streaming_sync(base_config: LocalModelConfig) -> None:
    sse_body = (
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
        'data: {"choices": [{"delta": {"content": " "}}]}\n\n'
        'data: {"choices": [{"delta": {"content": "World"}}]}\n\n'
        'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        req_data = json.loads(request.read())
        assert req_data["stream"] is True
        return httpx.Response(
            200,
            content=sse_body.encode("utf-8"),
            headers={"Content-Type": "text/event-stream"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    messages = [ChatMessage.user("Tell me a story")]
    chunks = list(adapter.stream(messages))

    text_parts = [c.delta_content for c in chunks if c.delta_content]
    assert "".join(text_parts) == "Hello World"
    assert chunks[-1].finish_reason == "stop"


@pytest.mark.asyncio
async def test_local_streaming_async(base_config: LocalModelConfig) -> None:
    sse_body = (
        'data: {"choices": [{"delta": {"content": "Async"}}]}\n\n'
        'data: {"choices": [{"delta": {"content": " Stream"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    async def ahandler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=sse_body.encode("utf-8"),
            headers={"Content-Type": "text/event-stream"},
        )

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(ahandler))
    adapter = LocalOpenWeightAdapter(base_config, async_client=async_client)

    messages = [ChatMessage.user("Test")]
    collected = []
    async for chunk in adapter.astream(messages):
        collected.append(chunk.delta_content)

    assert "".join(collected) == "Async Stream"


def test_local_generate_structured_success(base_config: LocalModelConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        resp_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"has_bugs": false, "summary": "Code is clean and verified."}',
                    },
                    "finish_reason": "stop",
                }
            ]
        }
        return httpx.Response(200, json=resp_payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    res = adapter.generate_structured(
        [ChatMessage.user("Review this function")],
        schema=CodeReviewResult,
    )
    assert isinstance(res, CodeReviewResult)
    assert res.has_bugs is False
    assert res.summary == "Code is clean and verified."


def test_local_connection_error_mapping(base_config: LocalModelConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused by localhost:11434")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    with pytest.raises(ProviderConnectionError) as exc_info:
        adapter.generate([ChatMessage.user("Hi")])
    assert "Cannot connect to local model server" in str(exc_info.value)


def test_local_timeout_error_mapping(base_config: LocalModelConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    with pytest.raises(InferenceTimeoutError):
        adapter.generate([ChatMessage.user("Hi")])


def test_local_http_404_model_not_found(base_config: LocalModelConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="model 'llama3.2:3b' not found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    with pytest.raises(ModelNotFoundError):
        adapter.generate([ChatMessage.user("Hi")])


def test_local_http_429_rate_limit(base_config: LocalModelConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Rate limit exceeded")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    with pytest.raises(RateLimitError):
        adapter.generate([ChatMessage.user("Hi")])


def test_local_http_400_context_length(base_config: LocalModelConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Maximum context length exceeded (8192 tokens)")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightAdapter(base_config, client=client)

    with pytest.raises(ContextLengthExceededError):
        adapter.generate([ChatMessage.user("Hi")])


def test_local_ping_success_and_failure(base_config: LocalModelConfig) -> None:
    # Success ping
    client_ok = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"data": []}))
    )
    adapter_ok = LocalOpenWeightAdapter(base_config, client=client_ok)
    assert adapter_ok.ping() is True

    # Failed ping
    client_fail = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(500, text="Server error"))
    )
    adapter_fail = LocalOpenWeightAdapter(base_config, client=client_fail)
    assert adapter_fail.ping() is False
