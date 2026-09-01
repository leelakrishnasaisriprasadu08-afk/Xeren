"""Local and open-weight model adapter supporting OpenAI-compatible local runtimes.

Compatible with Ollama, vLLM, llama.cpp server, LM Studio, LocalAI, and TGI.
"""

import json
import logging
import time
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional
import httpx

from xeren.models.base import BaseLLM
from xeren.models.config import LocalModelConfig, ModelConfig
from xeren.models.errors import (
    AuthenticationError,
    ContextLengthExceededError,
    InferenceTimeoutError,
    LLMError,
    ModelNotFoundError,
    ProviderConnectionError,
    RateLimitError,
)
from xeren.models.types import (
    ChatMessage,
    FunctionCall,
    LLMResponse,
    Role,
    StreamChunk,
    TokenUsage,
    ToolCall,
)

logger = logging.getLogger("xeren.models.local_openweight")


class LocalOpenWeightAdapter(BaseLLM):
    """Adapter for local and open-weight LLMs exposing OpenAI-compatible endpoints."""

    def __init__(
        self,
        config: ModelConfig,
        client: Optional[httpx.Client] = None,
        async_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(config)
        self._custom_client = client
        self._custom_async_client = async_client

    def _get_api_base(self, config: ModelConfig) -> str:
        base = config.api_base or "http://localhost:11434/v1"
        return base.rstrip("/")

    def _get_headers(self, config: ModelConfig) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        return headers

    def _format_messages_payload(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for msg in messages:
            item: Dict[str, Any] = {"role": msg.role.value, "content": msg.content or ""}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(item)
        return formatted

    def _build_payload(
        self,
        messages: List[ChatMessage],
        config: ModelConfig,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": config.model_id,
            "messages": self._format_messages_payload(messages),
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": stream,
        }
        if config.max_tokens is not None:
            payload["max_tokens"] = config.max_tokens
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        payload.update(config.extra_params)
        payload.update(kwargs)
        return payload

    def _map_http_error(self, err: Exception, status_code: Optional[int] = None, response_text: str = "") -> LLMError:
        text_lower = response_text.lower()
        if status_code == 401 or status_code == 403:
            return AuthenticationError(f"Authentication failed with endpoint: {response_text}", raw_error=err)
        if status_code == 404:
            return ModelNotFoundError(f"Model or endpoint not found: {response_text}", raw_error=err)
        if status_code == 429:
            return RateLimitError(f"Rate limit or quota exceeded: {response_text}", raw_error=err)
        if status_code == 400 and ("context length" in text_lower or "token limit" in text_lower or "maximum context" in text_lower):
            return ContextLengthExceededError(f"Context length exceeded: {response_text}", raw_error=err)
        return LLMError(f"Local model request failed (HTTP {status_code}): {response_text}", raw_error=err)

    def _parse_response_json(self, data: Dict[str, Any], model_id: str) -> LLMResponse:
        choices = data.get("choices", [])
        if not choices:
            raise LLMError("Provider returned an empty choice list", raw_error=data)

        first_choice = choices[0]
        msg_data = first_choice.get("message", {})
        content = msg_data.get("content") or ""
        finish_reason = first_choice.get("finish_reason") or "stop"

        tool_calls = None
        if "tool_calls" in msg_data and msg_data["tool_calls"]:
            tool_calls = [
                ToolCall(
                    id=tc.get("id", ""),
                    type=tc.get("type", "function"),
                    function=FunctionCall(
                        name=tc.get("function", {}).get("name", ""),
                        arguments=tc.get("function", {}).get("arguments", "{}"),
                    ),
                )
                for tc in msg_data["tool_calls"]
            ]

        chat_msg = ChatMessage(
            role=Role(msg_data.get("role", "assistant")),
            content=content,
            tool_calls=tool_calls,
        )

        usage_data = data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMResponse(
            content=content,
            message=chat_msg,
            finish_reason=finish_reason,
            usage=usage,
            model_id=data.get("model", model_id),
            raw_response=data,
        )

    def generate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        active_config = self._resolve_config(config)
        api_base = self._get_api_base(active_config)
        endpoint = f"{api_base}/chat/completions"
        payload = self._build_payload(messages, active_config, stream=False, **kwargs)
        headers = self._get_headers(active_config)

        logger.debug(
            "Dispatching sync inference to local model",
            extra={"model": active_config.model_id, "endpoint": endpoint, "messages_count": len(messages)},
        )

        start_time = time.perf_counter()
        try:
            if self._custom_client:
                resp = self._custom_client.post(
                    endpoint, json=payload, headers=headers, timeout=active_config.timeout_seconds
                )
            else:
                with httpx.Client(timeout=active_config.timeout_seconds) as client:
                    resp = client.post(endpoint, json=payload, headers=headers)

            if resp.status_code >= 400:
                raise self._map_http_error(
                    Exception(f"HTTP {resp.status_code}"),
                    status_code=resp.status_code,
                    response_text=resp.text,
                )

            data = resp.json()
            latency = time.perf_counter() - start_time
            parsed_response = self._parse_response_json(data, active_config.model_id)

            logger.info(
                "Local model inference completed",
                extra={
                    "model": parsed_response.model_id,
                    "latency_sec": round(latency, 3),
                    "total_tokens": parsed_response.usage.total_tokens,
                },
            )
            return parsed_response

        except httpx.ConnectError as err:
            logger.error("Failed to connect to local model server at %s: %s", endpoint, err)
            raise ProviderConnectionError(
                f"Cannot connect to local model server at {endpoint}. Ensure service (e.g. Ollama/vLLM) is running.",
                raw_error=err,
            ) from err
        except (httpx.TimeoutException, httpx.ReadTimeout, httpx.WriteTimeout) as err:
            logger.error("Inference timed out on %s: %s", endpoint, err)
            raise InferenceTimeoutError(
                f"Inference request timed out after {active_config.timeout_seconds}s.",
                raw_error=err,
            ) from err
        except LLMError:
            raise
        except Exception as err:
            logger.error("Unexpected error during local inference: %s", err)
            raise LLMError(f"Unexpected error during inference: {err}", raw_error=err) from err

    async def agenerate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        active_config = self._resolve_config(config)
        api_base = self._get_api_base(active_config)
        endpoint = f"{api_base}/chat/completions"
        payload = self._build_payload(messages, active_config, stream=False, **kwargs)
        headers = self._get_headers(active_config)

        logger.debug(
            "Dispatching async inference to local model",
            extra={"model": active_config.model_id, "endpoint": endpoint, "messages_count": len(messages)},
        )

        start_time = time.perf_counter()
        try:
            if self._custom_async_client:
                resp = await self._custom_async_client.post(
                    endpoint, json=payload, headers=headers, timeout=active_config.timeout_seconds
                )
            else:
                async with httpx.AsyncClient(timeout=active_config.timeout_seconds) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)

            if resp.status_code >= 400:
                raise self._map_http_error(
                    Exception(f"HTTP {resp.status_code}"),
                    status_code=resp.status_code,
                    response_text=resp.text,
                )

            data = resp.json()
            latency = time.perf_counter() - start_time
            parsed_response = self._parse_response_json(data, active_config.model_id)

            logger.info(
                "Local model async inference completed",
                extra={
                    "model": parsed_response.model_id,
                    "latency_sec": round(latency, 3),
                    "total_tokens": parsed_response.usage.total_tokens,
                },
            )
            return parsed_response

        except httpx.ConnectError as err:
            logger.error("Failed to connect to local model server at %s: %s", endpoint, err)
            raise ProviderConnectionError(
                f"Cannot connect to local model server at {endpoint}. Ensure service (e.g. Ollama/vLLM) is running.",
                raw_error=err,
            ) from err
        except (httpx.TimeoutException, httpx.ReadTimeout, httpx.WriteTimeout) as err:
            logger.error("Async inference timed out on %s: %s", endpoint, err)
            raise InferenceTimeoutError(
                f"Inference request timed out after {active_config.timeout_seconds}s.",
                raw_error=err,
            ) from err
        except LLMError:
            raise
        except Exception as err:
            logger.error("Unexpected error during local async inference: %s", err)
            raise LLMError(f"Unexpected error during async inference: {err}", raw_error=err) from err

    def stream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> Iterator[StreamChunk]:
        active_config = self._resolve_config(config)
        api_base = self._get_api_base(active_config)
        endpoint = f"{api_base}/chat/completions"
        payload = self._build_payload(messages, active_config, stream=True, **kwargs)
        headers = self._get_headers(active_config)

        try:
            if self._custom_client:
                with self._custom_client.stream(
                    "POST", endpoint, json=payload, headers=headers, timeout=active_config.timeout_seconds
                ) as resp:
                    if resp.status_code >= 400:
                        resp.read()
                        raise self._map_http_error(
                            Exception(f"HTTP {resp.status_code}"),
                            status_code=resp.status_code,
                            response_text=resp.text,
                        )
                    yield from self._process_stream_lines(resp.iter_lines())
            else:
                with httpx.Client(timeout=active_config.timeout_seconds) as client:
                    with client.stream("POST", endpoint, json=payload, headers=headers) as resp:
                        if resp.status_code >= 400:
                            resp.read()
                            raise self._map_http_error(
                                Exception(f"HTTP {resp.status_code}"),
                                status_code=resp.status_code,
                                response_text=resp.text,
                            )
                        yield from self._process_stream_lines(resp.iter_lines())
        except httpx.ConnectError as err:
            raise ProviderConnectionError(
                f"Cannot connect to local model server at {endpoint}.",
                raw_error=err,
            ) from err
        except (httpx.TimeoutException, httpx.ReadTimeout, httpx.WriteTimeout) as err:
            raise InferenceTimeoutError(
                f"Stream timed out after {active_config.timeout_seconds}s.",
                raw_error=err,
            ) from err

    async def astream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        active_config = self._resolve_config(config)
        api_base = self._get_api_base(active_config)
        endpoint = f"{api_base}/chat/completions"
        payload = self._build_payload(messages, active_config, stream=True, **kwargs)
        headers = self._get_headers(active_config)

        try:
            if self._custom_async_client:
                async with self._custom_async_client.stream(
                    "POST", endpoint, json=payload, headers=headers, timeout=active_config.timeout_seconds
                ) as resp:
                    if resp.status_code >= 400:
                        await resp.aread()
                        raise self._map_http_error(
                            Exception(f"HTTP {resp.status_code}"),
                            status_code=resp.status_code,
                            response_text=resp.text,
                        )
                    async for chunk in self._aprocess_stream_lines(resp.aiter_lines()):
                        yield chunk
            else:
                async with httpx.AsyncClient(timeout=active_config.timeout_seconds) as client:
                    async with client.stream("POST", endpoint, json=payload, headers=headers) as resp:
                        if resp.status_code >= 400:
                            await resp.aread()
                            raise self._map_http_error(
                                Exception(f"HTTP {resp.status_code}"),
                                status_code=resp.status_code,
                                response_text=resp.text,
                            )
                        async for chunk in self._aprocess_stream_lines(resp.aiter_lines()):
                            yield chunk
        except httpx.ConnectError as err:
            raise ProviderConnectionError(
                f"Cannot connect to local model server at {endpoint}.",
                raw_error=err,
            ) from err
        except (httpx.TimeoutException, httpx.ReadTimeout, httpx.WriteTimeout) as err:
            raise InferenceTimeoutError(
                f"Async stream timed out after {active_config.timeout_seconds}s.",
                raw_error=err,
            ) from err

    def _process_stream_lines(self, lines: Iterator[str]) -> Iterator[StreamChunk]:
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith(":"):
                continue
            if line_str.startswith("data: "):
                raw_data = line_str[6:].strip()
                if raw_data == "[DONE]":
                    break
                try:
                    data = json.loads(raw_data)
                    chunk = self._parse_stream_chunk_data(data)
                    if chunk:
                        yield chunk
                except json.JSONDecodeError:
                    continue

    async def _aprocess_stream_lines(self, lines: AsyncIterator[str]) -> AsyncIterator[StreamChunk]:
        async for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith(":"):
                continue
            if line_str.startswith("data: "):
                raw_data = line_str[6:].strip()
                if raw_data == "[DONE]":
                    break
                try:
                    data = json.loads(raw_data)
                    chunk = self._parse_stream_chunk_data(data)
                    if chunk:
                        yield chunk
                except json.JSONDecodeError:
                    continue

    def _parse_stream_chunk_data(self, data: Dict[str, Any]) -> Optional[StreamChunk]:
        choices = data.get("choices", [])
        if not choices:
            return None
        choice = choices[0]
        delta = choice.get("delta", {})
        delta_content = delta.get("content") or ""
        finish_reason = choice.get("finish_reason")
        return StreamChunk(
            delta_content=delta_content,
            finish_reason=finish_reason,
        )

    def ping(self) -> bool:
        """Check if local endpoint is reachable."""
        api_base = self._get_api_base(self.config)
        endpoint = f"{api_base}/models"
        try:
            if self._custom_client:
                resp = self._custom_client.get(endpoint, timeout=5.0)
                return resp.status_code == 200
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(endpoint)
                return resp.status_code == 200
        except Exception:
            return False

    async def aping(self) -> bool:
        """Asynchronously check if local endpoint is reachable."""
        api_base = self._get_api_base(self.config)
        endpoint = f"{api_base}/models"
        try:
            if self._custom_async_client:
                resp = await self._custom_async_client.get(endpoint, timeout=5.0)
                return resp.status_code == 200
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoint)
                return resp.status_code == 200
        except Exception:
            return False
