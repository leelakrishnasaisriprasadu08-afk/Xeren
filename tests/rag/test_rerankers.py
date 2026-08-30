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
