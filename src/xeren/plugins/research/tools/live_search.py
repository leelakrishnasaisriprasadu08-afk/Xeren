"""Live web search engines with bounded retries, rate limiting, and response normalization."""

from abc import ABC, abstractmethod
import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from xeren.plugins.research.schemas import RawSearchResult
from xeren.plugins.research.tools.search import BaseSearchEngine, MockSearchEngine
from xeren.plugins.research.tools.search_config import (
    SearchAuthError,
    SearchConfig,
    SearchProvider,
    SearchProviderError,
    SearchRateLimitError,
    SearchTimeoutError,
    mask_api_key,
    sanitize_message,
)

logger = logging.getLogger("xeren.plugins.research.tools.live_search")


class BaseLiveSearchEngine(BaseSearchEngine, ABC):
    """Abstract base class for live HTTP-based search providers."""

    def __init__(
        self,
        config: Optional[SearchConfig] = None,
        client: Optional[httpx.Client] = None,
        async_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.config = config or SearchConfig.from_env()
        self._client = client
        self._async_client = async_client

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the search provider."""
        pass

    @abstractmethod
    def _build_request(
        self,
        query: str,
        max_results: int,
        domains: Optional[List[str]],
    ) -> httpx.Request:
        """Construct the httpx.Request for the provider."""
        pass

    @abstractmethod
    def _normalize_response(self, data: Dict[str, Any]) -> List[RawSearchResult]:
        """Normalize raw provider JSON into standardized RawSearchResult objects."""
        pass

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers=self.config.headers,
            )
        return self._client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers=self.config.headers,
            )
        return self._async_client

    def _calculate_backoff(self, attempt: int, retry_after: Optional[float] = None) -> float:
        if retry_after is not None and retry_after > 0:
            return min(10.0, retry_after)
        delay = self.config.backoff_factor * (2 ** attempt) + random.uniform(0.01, 0.1)
        return min(10.0, delay)

    def _parse_retry_after(self, response: httpx.Response) -> Optional[float]:
        retry_hdr = response.headers.get("Retry-After")
        if retry_hdr:
            try:
                return float(retry_hdr)
            except ValueError:
                return None
        return None

    def _handle_response_errors(self, response: httpx.Response, attempt: int) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return

        body_preview = sanitize_message(response.text[:200], self.config.api_key)

        if status in (401, 403):
            raise SearchAuthError(
                message=f"Authentication failed: {body_preview}",
                provider=self.provider_name,
                status_code=status,
            )

        if status == 429:
            retry_after = self._parse_retry_after(response)
            if attempt >= self.config.max_retries:
                raise SearchRateLimitError(
                    message=f"Rate limit exceeded after {attempt + 1} attempts: {body_preview}",
                    provider=self.provider_name,
                    retry_after=retry_after,
                )
            # Transient, caller will sleep and retry
            return

        if status >= 500:
            if attempt >= self.config.max_retries:
                raise SearchProviderError(
                    message=f"Server error after {attempt + 1} attempts: {body_preview}",
                    provider=self.provider_name,
                    status_code=status,
                )
            return

        # Other 4xx client errors
        raise SearchProviderError(
            message=f"Client request error: {body_preview}",
            provider=self.provider_name,
            status_code=status,
        )

    def _execute_http(self, request: httpx.Request) -> Dict[str, Any]:
        client = self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(
                    "Sending search request (attempt %d/%d) to %s",
                    attempt + 1,
                    self.config.max_retries + 1,
                    request.url,
                )
                response = client.send(request)

                if response.status_code == 429:
                    self._handle_response_errors(response, attempt)
                    wait_time = self._calculate_backoff(attempt, self._parse_retry_after(response))
                    logger.warning("Rate limit hit on %s. Sleeping %.2fs before retry", self.provider_name, wait_time)
                    time.sleep(wait_time)
                    continue

                if response.status_code >= 500:
                    self._handle_response_errors(response, attempt)
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning("HTTP %d on %s. Sleeping %.2fs before retry", response.status_code, self.provider_name, wait_time)
                    time.sleep(wait_time)
                    continue

                self._handle_response_errors(response, attempt)

                try:
                    return response.json()
                except Exception as json_err:
                    raise SearchProviderError(
                        message=f"Malformed JSON response from {self.provider_name}: {json_err}",
                        provider=self.provider_name,
                        raw_error=json_err,
                    ) from json_err

            except httpx.TimeoutException as err:
                last_error = err
                if attempt < self.config.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning("Timeout on %s. Sleeping %.2fs before retry", self.provider_name, wait_time)
                    time.sleep(wait_time)
                    continue
                raise SearchTimeoutError(
                    message=f"Search request timed out after {self.config.timeout_seconds:.1f}s",
                    provider=self.provider_name,
                    raw_error=err,
                ) from err

            except (httpx.NetworkError, httpx.ConnectError) as err:
                last_error = err
                if attempt < self.config.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning("Network failure on %s. Sleeping %.2fs before retry: %s", self.provider_name, wait_time, err)
                    time.sleep(wait_time)
                    continue
                raise SearchProviderError(
                    message=f"Network connection failure with {self.provider_name}: {err}",
                    provider=self.provider_name,
                    raw_error=err,
                ) from err

        if last_error:
            raise SearchProviderError(
                message=f"Failed search after retries: {last_error}",
                provider=self.provider_name,
                raw_error=last_error,
            )
        return {}

    async def _aexecute_http(self, request: httpx.Request) -> Dict[str, Any]:
        client = self._get_async_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.send(request)

                if response.status_code == 429:
                    self._handle_response_errors(response, attempt)
                    wait_time = self._calculate_backoff(attempt, self._parse_retry_after(response))
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code >= 500:
                    self._handle_response_errors(response, attempt)
                    wait_time = self._calculate_backoff(attempt)
                    await asyncio.sleep(wait_time)
                    continue

                self._handle_response_errors(response, attempt)

                try:
                    return response.json()
                except Exception as json_err:
                    raise SearchProviderError(
                        message=f"Malformed JSON response from {self.provider_name}: {json_err}",
                        provider=self.provider_name,
                        raw_error=json_err,
                    ) from json_err

            except httpx.TimeoutException as err:
                last_error = err
                if attempt < self.config.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    await asyncio.sleep(wait_time)
                    continue
                raise SearchTimeoutError(
                    message=f"Search request timed out after {self.config.timeout_seconds:.1f}s",
                    provider=self.provider_name,
                    raw_error=err,
                ) from err

            except (httpx.NetworkError, httpx.ConnectError) as err:
                last_error = err
                if attempt < self.config.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    await asyncio.sleep(wait_time)
                    continue
                raise SearchProviderError(
                    message=f"Network connection failure with {self.provider_name}: {err}",
                    provider=self.provider_name,
                    raw_error=err,
                ) from err

        if last_error:
            raise SearchProviderError(
                message=f"Failed async search after retries: {last_error}",
                provider=self.provider_name,
                raw_error=last_error,
            )
        return {}

    def search(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        if not query.strip():
            return []

        request = self._build_request(query=query, max_results=max_results, domains=domains)
        payload = self._execute_http(request)
        results = self._normalize_response(payload)

        # Domain post-filter if not natively filtered
        if domains:
            results = [r for r in results if any(d.lower() in r.url.lower() for d in domains)]

        return results[:max_results]

    async def asearch(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        if not query.strip():
            return []

        request = self._build_request(query=query, max_results=max_results, domains=domains)
        payload = await self._aexecute_http(request)
        results = self._normalize_response(payload)

        if domains:
            results = [r for r in results if any(d.lower() in r.url.lower() for d in domains)]

        return results[:max_results]

    def ping(self) -> bool:
        if not self.config.api_key:
            return False
        return True

    async def aping(self) -> bool:
        return self.ping()

    def close(self) -> None:
        """Close underlying HTTP clients."""
        if self._client and not self._client.is_closed:
            self._client.close()

    async def aclose(self) -> None:
        """Asynchronously close underlying HTTP clients."""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()


class TavilySearchEngine(BaseLiveSearchEngine):
    """Production search provider integrating the Tavily Search API."""

    @property
    def provider_name(self) -> str:
        return "tavily"

    def _build_request(
        self,
        query: str,
        max_results: int,
        domains: Optional[List[str]],
    ) -> httpx.Request:
        base_url = self.config.base_url or "https://api.tavily.com"
        endpoint = f"{base_url.rstrip('/')}/search"

        payload: Dict[str, Any] = {
            "api_key": self.config.api_key or "",
            "query": query,
            "max_results": max_results,
            "search_depth": self.config.extra.get("search_depth", "basic"),
            "include_answer": False,
            "include_raw_content": False,
        }
        if domains:
            payload["include_domains"] = domains

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Xeren-Research/0.1.0",
        }
        headers.update(self.config.headers)

        return httpx.Request("POST", endpoint, headers=headers, json=payload)

    def _normalize_response(self, data: Dict[str, Any]) -> List[RawSearchResult]:
        raw_items = data.get("results")
        if not raw_items or not isinstance(raw_items, list):
            return []

        normalized: List[RawSearchResult] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue

            title = str(item.get("title", "")).strip() or url
            snippet = str(item.get("content", "")).strip()
            full_content = item.get("raw_content") or snippet

            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            try:
                score = float(item.get("score", 0.85))
            except (ValueError, TypeError):
                score = 0.85

            normalized.append(
                RawSearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    full_content=str(full_content) if full_content else None,
                    published_date=item.get("published_date"),
                    author=domain or None,
                    score=score,
                )
            )
        return normalized


class BraveSearchEngine(BaseLiveSearchEngine):
    """Production search provider integrating the Brave Search API."""

    @property
    def provider_name(self) -> str:
        return "brave"

    def _build_request(
        self,
        query: str,
        max_results: int,
        domains: Optional[List[str]],
    ) -> httpx.Request:
        base_url = self.config.base_url or "https://api.search.brave.com"
        endpoint = f"{base_url.rstrip('/')}/res/v1/web/search"

        params: Dict[str, Any] = {
            "q": query,
            "count": min(20, max_results),
        }
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.config.api_key or "",
            "User-Agent": "Xeren-Research/0.1.0",
        }
        headers.update(self.config.headers)

        return httpx.Request("GET", endpoint, headers=headers, params=params)

    def _normalize_response(self, data: Dict[str, Any]) -> List[RawSearchResult]:
        web_section = data.get("web", {})
        results_list = web_section.get("results") if isinstance(web_section, dict) else None
        if not results_list or not isinstance(results_list, list):
            return []

        normalized: List[RawSearchResult] = []
        for idx, item in enumerate(results_list):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue

            title = str(item.get("title", "")).strip() or url
            snippet = str(item.get("description", "")).strip()
            page_age = item.get("page_age")

            parsed = urlparse(url)
            domain = parsed.netloc

            # Positional decay for confidence scoring
            score = max(0.4, round(0.95 - (idx * 0.05), 2))

            normalized.append(
                RawSearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    full_content=snippet,
                    published_date=str(page_age) if page_age else None,
                    author=domain or None,
                    score=score,
                )
            )
        return normalized


class SearxngSearchEngine(BaseLiveSearchEngine):
    """Production search provider integrating a self-hosted or public SearXNG instance."""

    @property
    def provider_name(self) -> str:
        return "searxng"

    def _build_request(
        self,
        query: str,
        max_results: int,
        domains: Optional[List[str]],
    ) -> httpx.Request:
        base_url = self.config.base_url or "http://localhost:8080"
        endpoint = f"{base_url.rstrip('/')}/search"

        params: Dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "Xeren-Research/0.1.0",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        headers.update(self.config.headers)

        return httpx.Request("GET", endpoint, headers=headers, params=params)

    def _normalize_response(self, data: Dict[str, Any]) -> List[RawSearchResult]:
        raw_items = data.get("results")
        if not raw_items or not isinstance(raw_items, list):
            return []

        normalized: List[RawSearchResult] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue

            title = str(item.get("title", "")).strip() or url
            snippet = str(item.get("content", "")).strip()
            published_date = item.get("publishedDate")
            score = float(item.get("score", 0.8)) if item.get("score") is not None else 0.8

            parsed = urlparse(url)

            normalized.append(
                RawSearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    full_content=snippet,
                    published_date=str(published_date) if published_date else None,
                    author=parsed.netloc or None,
                    score=min(1.0, max(0.1, score)),
                )
            )
        return normalized


class GenericHttpSearchEngine(BaseLiveSearchEngine):
    """Generic configurable REST search provider."""

    @property
    def provider_name(self) -> str:
        return "generic"

    def _build_request(
        self,
        query: str,
        max_results: int,
        domains: Optional[List[str]],
    ) -> httpx.Request:
        base_url = self.config.base_url or "http://localhost:8000"
        endpoint = f"{base_url.rstrip('/')}/search"
        params = {"query": query, "limit": max_results}
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        headers.update(self.config.headers)
        return httpx.Request("GET", endpoint, headers=headers, params=params)

    def _normalize_response(self, data: Dict[str, Any]) -> List[RawSearchResult]:
        items = data.get("results") or data.get("items") or []
        normalized: List[RawSearchResult] = []
        for item in items:
            if isinstance(item, dict):
                url = str(item.get("url", ""))
                if url:
                    normalized.append(
                        RawSearchResult(
                            url=url,
                            title=str(item.get("title", url)),
                            snippet=str(item.get("snippet") or item.get("content") or ""),
                            score=float(item.get("score", 0.8)),
                        )
                    )
        return normalized


def create_search_engine(config: Optional[SearchConfig] = None) -> BaseSearchEngine:
    """Factory function creating the appropriate search engine based on configuration.

    Defaults to MockSearchEngine if no live provider or API key is configured.
    """
    resolved_config = config or SearchConfig.from_env()
    provider = resolved_config.provider.lower()

    if provider == SearchProvider.TAVILY.value:
        return TavilySearchEngine(resolved_config)
    elif provider == SearchProvider.BRAVE.value:
        return BraveSearchEngine(resolved_config)
    elif provider == SearchProvider.SEARXNG.value:
        return SearxngSearchEngine(resolved_config)
    elif provider == SearchProvider.GENERIC.value:
        return GenericHttpSearchEngine(resolved_config)
    else:
        # Default deterministic mock provider
        return MockSearchEngine()


__all__ = [
    "BaseLiveSearchEngine",
    "TavilySearchEngine",
    "BraveSearchEngine",
    "SearxngSearchEngine",
    "GenericHttpSearchEngine",
    "create_search_engine",
]
