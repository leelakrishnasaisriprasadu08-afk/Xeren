"""Unit tests for the 8-step ResearchWorkflow."""

import pytest

from xeren.plugins.research.schemas import (
    ResearchDepth,
    ResearchInput,
    ResearchResult,
)
from xeren.plugins.research.tools.search import MockSearchEngine
from xeren.plugins.research.workflow import ResearchWorkflow


def test_step_1_understand_objective() -> None:
    workflow = ResearchWorkflow()
    inp = ResearchInput(query="  Reinforcement learning from human feedback  ")
    objective = workflow.step_understand_objective(inp)
    assert objective == "Reinforcement learning from human feedback"


def test_step_2_query_generation_by_depth() -> None:
    workflow = ResearchWorkflow()

    # Overview: 1 query
    queries_overview = workflow.step_generate_queries("Diffusion Models", ResearchDepth.OVERVIEW)
    assert len(queries_overview) == 1
    assert queries_overview[0].query_text == "Diffusion Models"

    # Standard: 3 queries
    queries_standard = workflow.step_generate_queries("Diffusion Models", ResearchDepth.STANDARD)
    assert len(queries_standard) == 3

    # Deep dive: 5 queries
    queries_deep = workflow.step_generate_queries("Diffusion Models", ResearchDepth.DEEP_DIVE)
    assert len(queries_deep) == 5


def test_step_3_and_4_search_and_collect() -> None:
    engine = MockSearchEngine()
    workflow = ResearchWorkflow(search_engine=engine)
    queries = workflow.step_generate_queries("Vector Databases", ResearchDepth.STANDARD)

    raw_results = workflow.step_execute_and_collect_search(queries, max_results_per_query=2)
    assert len(raw_results) > 0
    assert len(engine.query_history) == len(queries)


def test_step_5_rank_sources() -> None:
    engine = MockSearchEngine()
    workflow = ResearchWorkflow(search_engine=engine)
    queries = workflow.step_generate_queries("Vector Databases", ResearchDepth.STANDARD)
    raw_results = workflow.step_execute_and_collect_search(queries, max_results_per_query=2)

    ranked = workflow.step_rank_sources(
        objective="Vector Databases",
        raw_results=raw_results,
        max_sources=3,
        min_relevance_score=0.2,
    )
    assert len(ranked) <= 3
    for r in ranked:
        assert r.relevance_score >= 0.2


def test_step_6_extract_evidence() -> None:
    workflow = ResearchWorkflow()
    ranked = workflow.step_rank_sources(
        objective="Vector Databases",
        raw_results=MockSearchEngine().search("Vector Databases", max_results=2),
        max_sources=2,
    )
    evidence = workflow.step_extract_evidence("Vector Databases", ranked)
    assert len(evidence) > 0
    assert evidence[0].citation_marker == "[1]"


def test_step_7_and_8_synthesize_and_assemble() -> None:
    workflow = ResearchWorkflow()
    inp = ResearchInput(query="Autonomous Agents", depth=ResearchDepth.STANDARD)
    result = workflow.run(inp)

    assert isinstance(result, ResearchResult)
    assert result.objective == "Autonomous Agents"
    assert len(result.executive_summary) > 0
    assert len(result.findings) > 0
    assert len(result.evidence) > 0
    assert len(result.sources) > 0
    assert len(result.queries_executed) == 3
    assert result.confidence_score > 0.0
    assert "latency_ms" in result.execution_stats


@pytest.mark.asyncio
async def test_workflow_arun() -> None:
    workflow = ResearchWorkflow()
    inp = ResearchInput(query="Graph Neural Networks", depth=ResearchDepth.OVERVIEW)
    result = await workflow.arun(inp)

    assert isinstance(result, ResearchResult)
    assert result.objective == "Graph Neural Networks"
    assert len(result.findings) > 0
    assert len(result.evidence) > 0


def test_workflow_empty_search_results_graceful_handling() -> None:
    # Empty search engine
    empty_engine = MockSearchEngine(default_results=[])
    workflow = ResearchWorkflow(search_engine=empty_engine)
    inp = ResearchInput(query="Obscure nonexistent concept 12345")

    result = workflow.run(inp)
    assert isinstance(result, ResearchResult)
    assert "No authoritative sources" in result.executive_summary
    assert len(result.findings) == 0
    assert len(result.evidence) == 0
    assert len(result.knowledge_gaps) > 0
    assert result.confidence_score <= 0.3
