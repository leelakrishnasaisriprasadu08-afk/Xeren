"""Unit tests for retrieval evaluation metrics."""

import pytest

from xeren.eval.retrieval_metrics import (
    HitRateEvaluator,
    MRREvaluator,
    PrecisionEvaluator,
    RecallEvaluator,
)
from xeren.eval.types import EvalSample
from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.types import SearchResult


@pytest.fixture
def retrieval_sample() -> EvalSample:
    c1 = DocumentChunk(chunk_id="c1", document_id="doc_a", content="A", chunk_index=0)
    c2 = DocumentChunk(chunk_id="c2", document_id="doc_b", content="B", chunk_index=0)
    c3 = DocumentChunk(chunk_id="c3", document_id="doc_c", content="C", chunk_index=0)

    results = [
        SearchResult(chunk=c1, score=0.9),
        SearchResult(chunk=c2, score=0.8),
        SearchResult(chunk=c3, score=0.7),
    ]

    return EvalSample(
        sample_id="sample-1",
        query="test query",
        expected_source_ids=["doc_b", "doc_d"],
        retrieved_chunks=results,
    )


def test_hit_rate_evaluator(retrieval_sample: EvalSample) -> None:
    # doc_b is at rank 2 (index 1), so hit_rate@1 is 0.0 and hit_rate@2 is 1.0
    hit1 = HitRateEvaluator(k=1).evaluate(retrieval_sample)
    assert hit1.score == 0.0

    hit2 = HitRateEvaluator(k=2).evaluate(retrieval_sample)
    assert hit2.score == 1.0


def test_mrr_evaluator(retrieval_sample: EvalSample) -> None:
    # doc_b is at rank 2, so MRR is 1/2 = 0.5
    mrr = MRREvaluator(k=5).evaluate(retrieval_sample)
    assert mrr.score == pytest.approx(0.5)


def test_precision_evaluator(retrieval_sample: EvalSample) -> None:
    # In top 3, only 1 chunk (c2/doc_b) is relevant out of 3 -> precision = 1/3
    prec = PrecisionEvaluator(k=3).evaluate(retrieval_sample)
    assert prec.score == pytest.approx(1.0 / 3.0)


def test_recall_evaluator(retrieval_sample: EvalSample) -> None:
    # Expected are doc_b and doc_d (total 2). Top 3 retrieved doc_b (1 found) -> recall = 1/2 = 0.5
    recall = RecallEvaluator(k=3).evaluate(retrieval_sample)
    assert recall.score == pytest.approx(0.5)
