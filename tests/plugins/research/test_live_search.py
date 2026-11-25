"""Unit and integration tests for live web search engines, configurations, retries, and normalization."""

import json
import os
from unittest.mock import patch
import httpx
import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.research.plugin import ResearchPlugin
from xeren.plugins.research.schemas import RawSearchResult, ResearchDepth, ResearchInput, ResearchResult
from xeren.plugins.research.tools.live_search import (
    BaseLiveSearchEngine,
    BraveSearchEngine,
    GenericHttpSearchEngine,
    SearxngSearchEngine,
    TavilySearchEngine,
    create_search_engine,
)
from xeren.plugins.research.tools.search import MockSearchEngine, SearchAdapter
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
from xeren.plugins.research.workflow import ResearchWorkflow


# -----------------------------------------------------------------------------
# 1. Configuration & Secret Masking Tests
# -----------------------------------------------------------------------------
def test_mask_api_key() -> None:
    assert mask_api_key(None) == "(none)"
    assert mask_api_key("") == "(none)"
    assert mask_api_key("12345") == "***"
    assert mask_api_key("tvly-abcdefghijklmnop1234") == "tvly...1234"


def test_sanitize_message_scrubs_secret() -> None:
    secret = "secret-key-9999"
    raw_error = f"Failed to authenticate with key {secret} on server"
    sanitized = sanitize_message(raw_error, secret)
    assert secret not in sanitized
    assert "secr...9999" in sanitized


def test_search_config_repr_hides_api_key() -> None:
    cfg = SearchConfig(provider="tavily", api_key="super-secret-key-value")
    rep = repr(cfg)
    assert "super-secret-key-value" not in rep


def test_search_config_from_env() -> None:
    with patch.dict(os.environ, {
        "XEREN_SEARCH_PROVIDER": "brave",
        "BRAVE_API_KEY": "brave-test-key-1234",
        "XEREN_SEARCH_TIMEOUT_SECONDS": "15.5",
        "XEREN_SEARCH_MAX_RETRIES": "5",
        "XEREN_SEARCH_BACKOFF_FACTOR": "0.2",
    }, clear=True):
        cfg = SearchConfig.from_env()
        assert cfg.provider == "brave"
        assert cfg.api_key == "brave-test-key-1234"
        assert cfg.timeout_seconds == 15.5
        assert cfg.max_retries == 5
        assert cfg.backoff_factor == 0.2


def test_search_config_auto_detection_from_keys() -> None:
    with patch.dict(os.environ, {"TAVILY_API_KEY": "tvly-test-1234"}, clear=True):
        cfg = SearchConfig.from_env()
        assert cfg.provider == "tavily"
        assert cfg.api_key == "tvly-test-1234"

    with patch.dict(os.environ, {"BRAVE_API_KEY": "brave-test-1234"}, clear=True):
        cfg = SearchConfig.from_env()
        assert cfg.provider == "brave"

    with patch.dict(os.environ, {"SEARXNG_URL": "http://my-searxng.org"}, clear=True):
        cfg = SearchConfig.from_env()
        assert cfg.provider == "searxng"
        assert cfg.base_url == "http://my-searxng.org"

    with patch.dict(os.environ, {}, clear=True):
        cfg = SearchConfig.from_env()
        assert cfg.provider == "mock"


# -----------------------------------------------------------------------------
# 2. Response Normalization Tests
# -----------------------------------------------------------------------------
def test_tavily_response_normalization() -> None:
    tavily_json = {
        "query": "Quantum Computing",
        "results": [
            {
                "title": "Quantum Supremacy Overview",
                "url": "https://nature.com/articles/quantum-1",
                "content": "Quantum processors achieve quantum computational advantage.",
                "raw_content": "Full article text on quantum processors.",
                "score": 0.98,
                "published_date": "2025-10-10",
            },
            {
                "title": "Quantum Algorithms",
                "url": "https://arxiv.org/abs/2501.1234",
                "content": "Shor and Grover algorithm review.",
                "score": 0.89,
            },
        ],
    }

    engine = TavilySearchEngine(SearchConfig(provider="tavily", api_key="dummy"))
    normalized = engine._normalize_response(tavily_json)

    assert len(normalized) == 2
    assert isinstance(normalized[0], RawSearchResult)
    assert normalized[0].url == "https://nature.com/articles/quantum-1"
    assert normalized[0].title == "Quantum Supremacy Overview"
    assert normalized[0].snippet == "Quantum processors achieve quantum computational advantage."
    assert normalized[0].full_content == "Full article text on quantum processors."
    assert normalized[0].score == 0.98
    assert normalized[0].published_date == "2025-10-10"
    assert normalized[0].author == "nature.com"

    assert normalized[1].score == 0.89
    assert normalized[1].author == "arxiv.org"


def test_brave_response_normalization() -> None:
    brave_json = {
        "web": {
            "results": [
                {
                    "title": "Brave Search Result 1",
                    "url": "https://example.com/page1",
                    "description": "Snippet description from Brave index.",
                    "page_age": "2026-01-01",
                },
                {
                    "title": "Brave Search Result 2",
                    "url": "https://example.com/page2",
                    "description": "Second snippet.",
                },
            ]
        }
    }

    engine = BraveSearchEngine(SearchConfig(provider="brave", api_key="dummy"))
    normalized = engine._normalize_response(brave_json)

    assert len(normalized) == 2
    assert normalized[0].url == "https://example.com/page1"
    assert normalized[0].title == "Brave Search Result 1"
    assert normalized[0].snippet == "Snippet description from Brave index."
    assert normalized[0].published_date == "2026-01-01"
    assert normalized[0].author == "example.com"
    assert normalized[0].score >= 0.8


def test_searxng_response_normalization() -> None:
    searxng_json = {
        "query": "Machine Learning",
        "results": [
            {
                "title": "ML Basics",
                "url": "https://ml.org/basics",
                "content": "Supervised and unsupervised learning.",
                "publishedDate": "2025-05-01",
                "score": 0.85,
            }
        ],
    }

    engine = SearxngSearchEngine(SearchConfig(provider="searxng"))
    normalized = engine._normalize_response(searxng_json)

    assert len(normalized) == 1
    assert normalized[0].url == "https://ml.org/basics"
    assert normalized[0].author == "ml.org"
    assert normalized[0].score == 0.85


def test_generic_http_response_normalization() -> None:
    generic_json = {
        "results": [
            {
                "url": "https://generic.org/item1",
                "title": "Generic Result",
                "content": "Generic content snippet",
                "score": 0.77,
            }
        ]
    }
    engine = GenericHttpSearchEngine(SearchConfig(provider="generic"))
    normalized = engine._normalize_response(generic_json)
    assert len(normalized) == 1
    assert normalized[0].url == "https://generic.org/item1"
    assert normalized[0].score == 0.77


# -----------------------------------------------------------------------------
# 3. Empty Results & Edge Cases
# -----------------------------------------------------------------------------
def test_empty_results_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"query": "test", "results": []})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="test-key"),
        client=client,
    )
    results = engine.search("obscure non-existent topic")
    assert results == []

    # Empty query returns empty immediately
    assert engine.search("   ") == []


@pytest.mark.asyncio
async def test_async_empty_results_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="test-key"),
        async_client=async_client,
    )
    results = await engine.asearch("anything")
    assert results == []


# -----------------------------------------------------------------------------
# 4. Timeout Handling
# -----------------------------------------------------------------------------
def test_timeout_handling_sync() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Socket read timed out")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="test-key", max_retries=1, backoff_factor=0.01),
        client=client,
    )

    with pytest.raises(SearchTimeoutError) as exc_info:
        engine.search("timeout query")
    assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_timeout_handling_async() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Async socket read timed out")

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="test-key", max_retries=1, backoff_factor=0.01),
        async_client=async_client,
    )

    with pytest.raises(SearchTimeoutError):
        await engine.asearch("async timeout query")


# -----------------------------------------------------------------------------
# 5. Rate Limit Handling (HTTP 429) & Retries
# -----------------------------------------------------------------------------
def test_rate_limit_retry_and_success() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, text="Too Many Requests")
        return httpx.Response(
            200,
            json={"results": [{"url": "https://ok.com", "title": "OK", "content": "Success after 429"}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="test-key", max_retries=2, backoff_factor=0.01),
        client=client,
    )
    results = engine.search("test rate limit recovery")
    assert len(results) == 1
    assert results[0].url == "https://ok.com"
    assert call_count == 2


def test_rate_limit_exhausted_raises_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0.01"}, text="Continuous Rate Limit")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="test-key", max_retries=1, backoff_factor=0.01),
        client=client,
    )

    with pytest.raises(SearchRateLimitError) as exc_info:
        engine.search("rate limit query")
    assert "Rate limit exceeded" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 6. Provider Authentication & Server Error Handling
# -----------------------------------------------------------------------------
def test_auth_error_no_retries_and_no_key_leak() -> None:
    secret_key = "super-secret-tvly-998877"
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, text=f"Unauthorized: key {secret_key} is invalid")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key=secret_key, max_retries=3),
        client=client,
    )

    with pytest.raises(SearchAuthError) as exc_info:
        engine.search("auth query")

    # Only 1 attempt; 401 should never retry
    assert call_count == 1
    # Secret must be scrubbed from exception message
    assert secret_key not in str(exc_info.value)


def test_server_500_retries_and_raises_provider_error() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="dummy", max_retries=2, backoff_factor=0.01),
        client=client,
    )

    with pytest.raises(SearchProviderError) as exc_info:
        engine.search("failing query")
    assert call_count == 3  # 1 initial + 2 retries
    assert "Server error" in str(exc_info.value)


def test_malformed_json_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="NOT VALID JSON {<broken>}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    engine = TavilySearchEngine(
        config=SearchConfig(provider="tavily", api_key="dummy"),
        client=client,
    )

    with pytest.raises(SearchProviderError) as exc_info:
        engine.search("broken response")
    assert "Malformed JSON" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 7. Factory create_search_engine Tests
# -----------------------------------------------------------------------------
def test_create_search_engine_factory() -> None:
    # Mock
    engine_mock = create_search_engine(SearchConfig(provider="mock"))
    assert isinstance(engine_mock, MockSearchEngine)

    # Tavily
    engine_tavily = create_search_engine(SearchConfig(provider="tavily", api_key="key"))
    assert isinstance(engine_tavily, TavilySearchEngine)

    # Brave
    engine_brave = create_search_engine(SearchConfig(provider="brave", api_key="key"))
    assert isinstance(engine_brave, BraveSearchEngine)

    # Searxng
    engine_searxng = create_search_engine(SearchConfig(provider="searxng", base_url="http://localhost"))
    assert isinstance(engine_searxng, SearxngSearchEngine)

    # Generic
    engine_generic = create_search_engine(SearchConfig(provider="generic", base_url="http://localhost"))
    assert isinstance(engine_generic, GenericHttpSearchEngine)


# -----------------------------------------------------------------------------
# 8. SearchAdapter Integration Test
# -----------------------------------------------------------------------------
def test_search_adapter_with_live_engine() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://adapter-source.org/data",
                        "title": "Adapter Verified Source",
                        "content": "Data points routed through SearchAdapter wrapper.",
                        "score": 0.94,
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    live_engine = TavilySearchEngine(SearchConfig(provider="tavily", api_key="key"), client=client)

    adapter = SearchAdapter(
        search_fn=live_engine.search,
        asearch_fn=live_engine.asearch,
        ping_fn=live_engine.ping,
    )

    assert adapter.ping() is True
    res = adapter.search("adapter test query", max_results=2)
    assert len(res) == 1
    assert res[0].url == "https://adapter-source.org/data"
    assert "SearchAdapter wrapper" in res[0].snippet


# -----------------------------------------------------------------------------
# 9. ResearchWorkflow End-to-End with Mocked Live Provider
# -----------------------------------------------------------------------------
def test_workflow_with_mocked_live_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://arxiv.org/abs/2405.0001",
                        "title": "Hierarchical Multi-Agent Architectures",
                        "content": "Empirical evaluations confirm that hierarchical agent architectures outperform monolithic systems in factual accuracy.",
                        "score": 0.96,
                        "published_date": "2025-08-14",
                    },
                    {
                        "url": "https://nature.com/articles/agent-benchmarks",
                        "title": "Agent Architectures Benchmark Standards",
                        "content": "Standardized benchmark protocols evaluate hierarchical agent architectures across distributed cognitive tools.",
                        "score": 0.91,
                        "published_date": "2025-09-02",
                    },
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    live_engine = TavilySearchEngine(SearchConfig(provider="tavily", api_key="test-api-key"), client=client)

    workflow = ResearchWorkflow(search_engine=live_engine)
    inp = ResearchInput(query="Hierarchical agent architectures", depth=ResearchDepth.STANDARD)

    result = workflow.run(inp)
    assert isinstance(result, ResearchResult)
    assert result.objective == "Hierarchical agent architectures"
    assert len(result.sources) >= 2
    assert any("arxiv.org" in s.url for s in result.sources)
    assert len(result.evidence) > 0
    assert any("factual accuracy" in ev.fact_statement for ev in result.evidence)
    assert len(result.findings) > 0
    assert result.confidence_score >= 0.7


# -----------------------------------------------------------------------------
# 10. XerenCore Live Search Provider Integration & Health Check
# -----------------------------------------------------------------------------
def test_core_with_live_search_engine_and_health() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://core-test.org/ai-systems",
                        "title": "Core Live Search Result",
                        "content": "Verified research payload delivered to Xeren Core.",
                        "score": 0.95,
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    live_engine = TavilySearchEngine(SearchConfig(provider="tavily", api_key="test-api-key"), client=client)

    core = XerenCore(search_engine=live_engine)

    # Verify health check reflects TavilySearchEngine
    health = core.check_health()
    assert health["healthy"] is True
    assert health["plugins"]["research"]["details"]["search_engine"] == "TavilySearchEngine"
    assert health["plugins"]["research"]["details"]["search_engine_healthy"] is True

    # Execute research through Core
    res = core.research("AI Systems Evaluation", depth=ResearchDepth.OVERVIEW)
    assert isinstance(res, ResearchResult)
    assert res.sources[0].url == "https://core-test.org/ai-systems"
    assert "Verified research payload" in res.evidence[0].fact_statement


def test_mock_search_engine_remains_deterministic() -> None:
    """Verify that MockSearchEngine remains 100% deterministic and unaffected by live search additions."""
    mock_engine = MockSearchEngine()
    res1 = mock_engine.search("Deterministic Test Query", max_results=3)
    res2 = mock_engine.search("Deterministic Test Query", max_results=3)

    assert len(res1) == 3
    assert len(res2) == 3
    for a, b in zip(res1, res2):
        assert a.url == b.url
        assert a.title == b.title
        assert a.snippet == b.snippet
        assert a.score == b.score
