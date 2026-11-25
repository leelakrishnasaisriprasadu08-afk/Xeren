"""Unit tests for RAG rerankers and threshold filtering."""

import pytest

from xeren.rag.document import DocumentChunk
from xeren.rag.rerankers.mock import MockReranker
from xeren.rag.rerankers.threshold import CompositeReranker, ScoreThresholdReranker
from xeren.rag.retrieval.types import SearchResult


@pytest.fixture
def scored_results() -> list[SearchResult]:
    c1 = DocumentChunk(chunk_id="c1", document_id="d1", content="Chunk 1", chunk_index=0)
    c2 = DocumentChunk(chunk_id="c2", document_id="d1", content="Chunk 2", chunk_index=1)
    c3 = DocumentChunk(chunk_id="c3", document_id="d2", content="Chunk 3", chunk_index=0)

    return [
        SearchResult(chunk=c1, score=0.9, retrieval_type="dense"),
        SearchResult(chunk=c2, score=0.4, retrieval_type="dense"),
        SearchResult(chunk=c3, score=0.7, retrieval_type="dense"),
    ]


def test_score_threshold_reranker_filters_low_scores(scored_results: list[SearchResult]) -> None:
    reranker = ScoreThresholdReranker(min_score=0.5)
    reranked = reranker.rerank("query", scored_results)

    # c2 (score 0.4) should be filtered out
    assert len(reranked) == 2
    assert [r.chunk.chunk_id for r in reranked] == ["c1", "c3"]


def test_score_threshold_reranker_top_n(scored_results: list[SearchResult]) -> None:
    reranker = ScoreThresholdReranker(min_score=0.0)
    reranked = reranker.rerank("query", scored_results, top_n=2)

    assert len(reranked) == 2
    assert reranked[0].chunk.chunk_id == "c1"  # 0.9
    assert reranked[1].chunk.chunk_id == "c3"  # 0.7


def test_mock_reranker_reordering(scored_results: list[SearchResult]) -> None:
    # Reverse ordering
    reranker = MockReranker(reverse_order=True)
    reranked = reranker.rerank("query", scored_results)

    assert [r.chunk.chunk_id for r in reranked] == ["c2", "c3", "c1"]


def test_composite_reranker(scored_results: list[SearchResult]) -> None:
    # First filter out < 0.5 (leaving c1 and c3), then reverse order (c3 then c1)
    threshold = ScoreThresholdReranker(min_score=0.5)
    mock = MockReranker(reverse_order=True)
    composite = CompositeReranker([threshold, mock])

    reranked = composite.rerank("query", scored_results)
    assert len(reranked) == 2
    assert [r.chunk.chunk_id for r in reranked] == ["c3", "c1"]


# ---------------------------------------------------------------------------
# LocalReranker tests
# ---------------------------------------------------------------------------

def test_local_reranker_reordering_by_joint_relevance() -> None:
    from xeren.rag.rerankers.local import LocalReranker

    # c_scattered had high first-stage retrieval score (0.85) but weak phrase cohesion
    c_scattered = DocumentChunk(
        chunk_id="chunk-scattered",
        document_id="doc-1",
        content="Distributed computing networks sometimes use a consensus protocol.",
        chunk_index=0,
        metadata={"title": "General Computing"},
    )
    # c_exact had lower first-stage retrieval score (0.45) but exact phrase & header match
    c_exact = DocumentChunk(
        chunk_id="chunk-exact",
        document_id="doc-2",
        content="Raft is a distributed consensus algorithm providing fault tolerance.",
        chunk_index=0,
        metadata={"title": "Raft Consensus", "header_path": "Architecture > Consensus"},
    )

    r_scattered = SearchResult(chunk=c_scattered, score=0.85, retrieval_type="dense")
    r_exact = SearchResult(chunk=c_exact, score=0.45, retrieval_type="dense")

    reranker = LocalReranker()
    query = "Raft distributed consensus algorithm"
    reranked = reranker.rerank(query, [r_scattered, r_exact])

    assert len(reranked) == 2
    # Exact phrase and header match chunk must be promoted to rank 1
    assert reranked[0].chunk.chunk_id == "chunk-exact"
    assert reranked[1].chunk.chunk_id == "chunk-scattered"

    # All output scores must be calibrated in [0.0, 1.0]
    assert all(0.0 <= r.score <= 1.0 for r in reranked)
    assert reranked[0].retrieval_type == "reranked"


def test_local_reranker_top_n_and_empty() -> None:
    from xeren.rag.rerankers.local import LocalReranker

    c1 = DocumentChunk(chunk_id="c1", document_id="d1", content="Python programming language", chunk_index=0)
    c2 = DocumentChunk(chunk_id="c2", document_id="d1", content="Rust memory safety", chunk_index=1)
    c3 = DocumentChunk(chunk_id="c3", document_id="d1", content="Java virtual machine", chunk_index=2)

    results = [
        SearchResult(chunk=c1, score=0.9),
        SearchResult(chunk=c2, score=0.8),
        SearchResult(chunk=c3, score=0.7),
    ]

    reranker = LocalReranker()

    # top_n truncation
    reranked = reranker.rerank("Python programming", results, top_n=2)
    assert len(reranked) == 2
    assert reranked[0].chunk.chunk_id == "c1"

    # empty results
    assert reranker.rerank("Python", []) == []

    # empty query preserves candidates up to top_n
    assert len(reranker.rerank("", results, top_n=2)) == 2


@pytest.mark.asyncio
async def test_local_reranker_async() -> None:
    from xeren.rag.rerankers.local import LocalReranker

    c1 = DocumentChunk(chunk_id="c1", document_id="d1", content="Machine learning models", chunk_index=0)
    r1 = SearchResult(chunk=c1, score=0.7)

    reranker = LocalReranker()
    reranked = await reranker.arerank("Machine learning", [r1])

    assert len(reranked) == 1
    assert reranked[0].chunk.chunk_id == "c1"
    assert 0.0 <= reranked[0].score <= 1.0
