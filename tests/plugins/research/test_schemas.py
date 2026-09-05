"""Unit tests for Research Plugin Pydantic schemas."""

import pytest
from pydantic import ValidationError

from xeren.plugins.research.schemas import (
    EvidenceItem,
    KeyFinding,
    RankedSource,
    RawSearchResult,
    ResearchDepth,
    ResearchInput,
    ResearchResult,
    SearchQuery,
)


def test_research_input_defaults() -> None:
    inp = ResearchInput(query="Quantum computing applications")
    assert inp.query == "Quantum computing applications"
    assert inp.depth == ResearchDepth.STANDARD
    assert inp.max_sources == 5
    assert inp.domains == []
    assert inp.min_relevance_score == 0.3
    assert inp.time_limit_seconds == 30.0
    assert inp.include_raw_sources is True


def test_research_input_validations() -> None:
    # Query too short (< 2 chars)
    with pytest.raises(ValidationError):
        ResearchInput(query="a")

    # max_sources out of bounds (< 1 or > 20)
    with pytest.raises(ValidationError):
        ResearchInput(query="valid query", max_sources=0)

    with pytest.raises(ValidationError):
        ResearchInput(query="valid query", max_sources=25)

    # min_relevance_score out of [0.0, 1.0]
    with pytest.raises(ValidationError):
        ResearchInput(query="valid query", min_relevance_score=1.5)


def test_search_query_and_raw_result() -> None:
    sq = SearchQuery(query_text="AI safety alignment", intent="overview", priority=1)
    assert sq.query_text == "AI safety alignment"
    assert sq.priority == 1

    raw = RawSearchResult(
        url="https://example.org/ai-safety",
        title="AI Safety Overview",
        snippet="Overview of alignment techniques.",
        score=0.92,
    )
    assert raw.url == "https://example.org/ai-safety"
    assert raw.score == 0.92


def test_ranked_source_and_evidence_item() -> None:
    src = RankedSource(
        source_id="src-1",
        url="https://example.org/src-1",
        title="Title 1",
        snippet="Snippet text",
        relevance_score=0.85,
        selected=True,
    )
    assert src.source_id == "src-1"
    assert src.selected is True

    ev = EvidenceItem(
        evidence_id="ev-1",
        fact_statement="Transformers scale effectively with compute.",
        source_id="src-1",
        source_url="https://example.org/src-1",
        confidence=0.95,
        citation_marker="[1]",
    )
    assert ev.evidence_id == "ev-1"
    assert ev.citation_marker == "[1]"


def test_research_result_and_markdown_report() -> None:
    finding = KeyFinding(
        topic="Scalability",
        summary="Empirical evidence demonstrates predictable scaling curves.",
        supporting_evidence_ids=["ev-1"],
        confidence=0.90,
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev-1",
            fact_statement="Compute scaling follows a power law.",
            source_id="src-1",
            source_url="https://example.org/scaling",
            confidence=0.95,
            citation_marker="[1]",
        )
    ]
    source = RankedSource(
        source_id="src-1",
        url="https://example.org/scaling",
        title="Scaling Laws for Neural Models",
        snippet="Empirical data on power laws.",
        relevance_score=0.91,
        selected=True,
    )

    res = ResearchResult(
        objective="Scaling behavior in large models",
        executive_summary="Summary of findings regarding scaling laws.",
        findings=[finding],
        evidence=evidence,
        sources=[source],
        queries_executed=["scaling behavior in large models"],
        knowledge_gaps=["Data exhaustion limitations"],
        contradictions=[],
        confidence_score=0.92,
        execution_stats={"latency_ms": 120.0},
    )

    report = res.to_markdown_report()
    assert "# Research Report: Scaling behavior in large models" in report
    assert "## Executive Summary" in report
    assert "### Scalability (Confidence: 90%)" in report
    assert "[1]" in report
    assert "Data exhaustion limitations" in report
