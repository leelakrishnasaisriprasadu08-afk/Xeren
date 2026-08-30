"""Local and open-weight embedding model adapter supporting OpenAI-compatible endpoints."""

import logging
from typing import Any, Dict, List, Optional
import httpx

from xeren.models.errors import (
    AuthenticationError,
    InferenceTimeoutError,
    LLMError,
    ModelNotFoundError,
    ProviderConnectionError,
    RateLimitError,
)
from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.embeddings.config import EmbeddingConfig

logger = logging.getLogger("xeren.rag.embeddings.local_openweight")


class LocalOpenWeightEmbeddingAdapter(BaseEmbeddingModel):
    """Adapter for local and open-weight embedding endpoints (Ollama, vLLM, TEI, LocalAI)."""

    def __init__(
        self,
        config: EmbeddingConfig,
        client: Optional[httpx.Client] = None,
        async_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(config)
        self._custom_client = client
        self._custom_async_client = async_client

    def _get_api_base(self) -> str:
        base = self.config.api_base or "http://localhost:11434/v1"
        return base.rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _map_http_error(self, err: Exception, status_code: Optional[int] = None, response_text: str = "") -> LLMError:
        if status_code == 401 or status_code == 403:
            return AuthenticationError(f"Authentication failed: {response_text}", raw_error=err)
        if status_code == 404:
            return ModelNotFoundError(f"Embedding model not found: {response_text}", raw_error=err)
        if status_code == 429:
            return RateLimitError(f"Rate limit exceeded: {response_text}", raw_error=err)
        return LLMError(f"Embedding request failed (HTTP {status_code}): {response_text}", raw_error=err)

    def _parse_embeddings_response(self, data: Dict[str, Any], expected_count: int) -> List[List[float]]:
        items = data.get("data", [])
        if not items:
            raise LLMError("Provider returned an empty embedding list", raw_error=data)

        # Sort by index if provided
        sorted_items = sorted(items, key=lambda x: x.get("index", 0))
        vectors = [item["embedding"] for item in sorted_items if "embedding" in item]

        if len(vectors) != expected_count:
            logger.warning(
                "Embedding count mismatch: expected %d, got %d", expected_count, len(vectors)
            )

        return vectors

    def embed_query(self, text: str) -> List[float]:
        results = self.embed_documents([text])
        if not results:
            raise LLMError("Failed to generate embedding for query")
        return results[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        api_base = self._get_api_base()
        endpoint = f"{api_base}/embeddings"
        headers = self._get_headers()
        batch_size = self.config.batch_size
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": self.config.model_id,
                "input": batch,
            }
            payload.update(self.config.extra_params)

            try:
                if self._custom_client:
                    resp = self._custom_client.post(
                        endpoint, json=payload, headers=headers, timeout=self.config.timeout_seconds
                    )
                else:
                    with httpx.Client(timeout=self.config.timeout_seconds) as client:
                        resp = client.post(endpoint, json=payload, headers=headers)

                if resp.status_code >= 400:
                    raise self._map_http_error(
                        Exception(f"HTTP {resp.status_code}"),
                        status_code=resp.status_code,
                        response_text=resp.text,
                    )

                data = resp.json()
                batch_vectors = self._parse_embeddings_response(data, len(batch))
                all_embeddings.extend(batch_vectors)

            except httpx.ConnectError as err:
                raise ProviderConnectionError(
                    f"Cannot connect to embedding endpoint at {endpoint}.", raw_error=err
                ) from err
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.WriteTimeout) as err:
                raise InferenceTimeoutError(
                    f"Embedding request timed out after {self.config.timeout_seconds}s.", raw_error=err
                ) from err
            except LLMError:
                raise
            except Exception as err:
                raise LLMError(f"Unexpected embedding error: {err}", raw_error=err) from err

        return all_embeddings

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        api_base = self._get_api_base()
        endpoint = f"{api_base}/embeddings"
        headers = self._get_headers()
        batch_size = self.config.batch_size
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": self.config.model_id,
                "input": batch,
            }
            payload.update(self.config.extra_params)

            try:
                if self._custom_async_client:
                    resp = await self._custom_async_client.post(
                        endpoint, json=payload, headers=headers, timeout=self.config.timeout_seconds
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                        resp = await client.post(endpoint, json=payload, headers=headers)

                if resp.status_code >= 400:
                    raise self._map_http_error(
                        Exception(f"HTTP {resp.status_code}"),
                        status_code=resp.status_code,
                        response_text=resp.text,
                    )

                data = resp.json()
                batch_vectors = self._parse_embeddings_response(data, len(batch))
                all_embeddings.extend(batch_vectors)

            except httpx.ConnectError as err:
                raise ProviderConnectionError(
                    f"Cannot connect to embedding endpoint at {endpoint}.", raw_error=err
                ) from err
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.WriteTimeout) as err:
                raise InferenceTimeoutError(
                    f"Async embedding request timed out after {self.config.timeout_seconds}s.",
                    raw_error=err,
                ) from err
            except LLMError:
                raise
            except Exception as err:
                raise LLMError(f"Unexpected async embedding error: {err}", raw_error=err) from err

        return all_embeddings

    async def aembed_query(self, text: str) -> List[float]:
        results = await self.aembed_documents([text])
        if not results:
            raise LLMError("Failed to generate async embedding for query")
        return results[0]

    def ping(self) -> bool:
        api_base = self._get_api_base()
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
        api_base = self._get_api_base()
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
