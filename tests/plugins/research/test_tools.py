"""Unit tests for Research Plugin internal tools and adapters."""

import pytest

from xeren.models.config import ModelConfig
from xeren.models.providers.mock import MockLLM
from xeren.plugins.research.schemas import (
    EvidenceItem,
    RankedSource,
    RawSearchResult,
)
from xeren.plugins.research.tools.evidence import EvidenceExtractionTool
from xeren.plugins.research.tools.ranking import SourceRankingTool
from xeren.plugins.research.tools.registry import ResearchToolRegistry
from xeren.plugins.research.tools.search import (
    BaseSearchEngine,
    MockSearchEngine,
    SearchAdapter,
)
from xeren.plugins.research.tools.synthesis import SynthesisTool
from xeren.rag.rerankers.threshold import ScoreThresholdReranker


def test_mock_search_engine_basic_and_canned() -> None:
    engine = MockSearchEngine()

    # Synthetic result generation
    results = engine.search("agent architectures", max_results=3)
    assert len(results) == 3
    assert "agent-architectures" in results[0].url
    assert "agent architectures" in engine.query_history

    # Canned result registration
    canned = [
        RawSearchResult(
            url="https://canned.org/article",
            title="Canned Result",
            snippet="Specific canned snippet for testing.",
            score=1.0,
        )
    ]
    engine.set_results("specific query", canned)
    matched = engine.search("this is a specific query for test", max_results=2)
    assert len(matched) == 1
    assert matched[0].url == "https://canned.org/article"


def test_mock_search_engine_domain_filtering() -> None:
    engine = MockSearchEngine()
    results = engine.search("machine learning", domains=["arxiv.org"])
    for r in results:
        assert "arxiv.org" in r.url


def test_mock_search_engine_error_and_ping() -> None:
    engine = MockSearchEngine(error_to_raise=ConnectionError("Search engine offline"), is_healthy=False)
    assert engine.ping() is False

    with pytest.raises(ConnectionError):
        engine.search("any query")


@pytest.mark.asyncio
async def test_mock_search_engine_async() -> None:
    engine = MockSearchEngine()
    results = await engine.asearch("async query", max_results=2)
    assert len(results) == 2
    assert await engine.aping() is True


def test_search_adapter_wrapper() -> None:
    def custom_search(query: str, max_results: int, domains: list[str] | None) -> list[RawSearchResult]:
        return [
            RawSearchResult(
                url=f"https://custom-provider.com/{query}",
                title=f"Custom: {query}",
                snippet=f"Snippet for {query}",
                score=0.99,
            )
        ]

    adapter = SearchAdapter(search_fn=custom_search, ping_fn=lambda: True)
    assert adapter.ping() is True

    res = adapter.search("neural networks", max_results=5)
    assert len(res) == 1
    assert res[0].url == "https://custom-provider.com/neural networks"


def test_source_ranking_tool() -> None:
    ranking_tool = SourceRankingTool()
    raw_results = [
        RawSearchResult(
            url="https://example.org/1",
            title="Quantum Computing Algorithms",
            snippet="Detailed overview of Shor's and Grover's quantum algorithms.",
            score=0.9,
        ),
        RawSearchResult(
            url="https://example.org/2",
            title="Irrelevant Recipe",
            snippet="Baking chocolate cookies with sugar and flour.",
            score=0.1,
        ),
        # Duplicate URL
        RawSearchResult(
            url="https://example.org/1",
            title="Duplicate Title",
            snippet="Duplicate snippet",
            score=0.8,
        ),
    ]

    ranked = ranking_tool.execute(
        objective="quantum computing algorithms",
        results=raw_results,
        max_sources=5,
        min_relevance_score=0.3,
    )

    # Duplicate removed
    urls = [r.url for r in ranked]
    assert urls == ["https://example.org/1"]
    assert ranked[0].source_id == "src-1"
    assert ranked[0].relevance_score >= 0.3


def test_source_ranking_with_rag_reranker() -> None:
    custom_reranker = ScoreThresholdReranker(min_score=0.4)
    ranking_tool = SourceRankingTool(reranker=custom_reranker)
    raw_results = [
        RawSearchResult(url="https://example.org/a", title="Python 3.12 Features", snippet="Python 3.12 type syntax", score=0.8),
        RawSearchResult(url="https://example.org/b", title="Ancient History", snippet="Roman empire history", score=0.1),
    ]
    ranked = ranking_tool.execute(
        objective="Python 3.12 syntax",
        results=raw_results,
        max_sources=2,
    )
    assert len(ranked) == 1
    assert ranked[0].url == "https://example.org/a"


def test_evidence_extraction_tool() -> None:
    tool = EvidenceExtractionTool()
    sources = [
        RankedSource(
            source_id="src-1",
            url="https://example.org/alpha",
            title="Transformer Scaling",
            snippet="Transformers exhibit power-law scaling with compute. Model loss drops predictably. Large models achieve superior sample efficiency.",
            relevance_score=0.9,
            selected=True,
        )
    ]

    evidence = tool.execute(objective="transformer scaling laws", sources=sources)
    assert len(evidence) >= 2
    assert evidence[0].source_id == "src-1"
    assert evidence[0].citation_marker == "[1]"
    assert evidence[0].source_url == "https://example.org/alpha"
    assert evidence[0].confidence >= 0.5


def test_synthesis_tool_deterministic() -> None:
    tool = SynthesisTool()
    sources = [
        RankedSource(
            source_id="src-1",
            url="https://example.org/1",
            title="Neural Scaling Laws",
            snippet="Predictable loss scaling.",
            relevance_score=0.92,
            selected=True,
        )
    ]
    evidence = [
        EvidenceItem(
            evidence_id="ev-1",
            fact_statement="Predictable loss scaling with compute.",
            source_id="src-1",
            source_url="https://example.org/1",
            confidence=0.92,
            citation_marker="[1]",
        )
    ]

    synthesis = tool.execute(
        objective="neural scaling",
        evidence=evidence,
        sources=sources,
        queries_executed=["neural scaling"],
    )

    assert "executive_summary" in synthesis
    assert len(synthesis["findings"]) == 1
    assert synthesis["findings"][0].topic == "Neural Scaling Laws"
    assert synthesis["confidence_score"] >= 0.8


def test_synthesis_tool_with_llm() -> None:
    mock_llm = MockLLM(
        canned_response="Synthetic models improve downstream reasoning when given verified context."
    )
    tool = SynthesisTool(llm=mock_llm)
    sources = [
        RankedSource(
            source_id="src-1",
            url="https://example.org/1",
            title="Reasoning Benchmark",
            snippet="Downstream reasoning improves with verified context.",
            relevance_score=0.95,
            selected=True,
        )
    ]
    evidence = [
        EvidenceItem(
            evidence_id="ev-1",
            fact_statement="Reasoning improves with verified context.",
            source_id="src-1",
            source_url="https://example.org/1",
            confidence=0.95,
            citation_marker="[1]",
        )
    ]

    synthesis = tool.execute(
        objective="reasoning evaluation",
        evidence=evidence,
        sources=sources,
    )
    assert "Synthetic models improve downstream reasoning" in synthesis["executive_summary"]


def test_research_tool_registry() -> None:
    registry = ResearchToolRegistry()
    assert registry.get("source_ranking") is not None
    assert registry.get("evidence_extraction") is not None
    assert registry.get("synthesis") is not None

    new_engine = MockSearchEngine()
    registry.set_search_engine(new_engine)
    assert registry.search_engine is new_engine

    new_llm = MockLLM()
    registry.set_llm(new_llm)
    assert registry.evidence_tool.llm is new_llm
    assert registry.synthesis_tool.llm is new_llm
