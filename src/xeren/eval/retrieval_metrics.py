"""Retrieval quality metrics: Hit Rate @ K, MRR @ K, Precision @ K, Recall @ K."""

from typing import List, Set

from xeren.eval.base import BaseEvaluator
from xeren.eval.types import EvalSample, MetricResult


class HitRateEvaluator(BaseEvaluator):
    """Calculates Hit Rate @ K: 1.0 if any expected source is retrieved in top K, else 0.0."""

    def __init__(self, k: int = 3) -> None:
        self.k = k

    @property
    def metric_name(self) -> str:
        return f"hit_rate@{self.k}"

    def evaluate(self, sample: EvalSample) -> MetricResult:
        if not sample.expected_source_ids:
            return MetricResult(metric_name=self.metric_name, score=1.0, details={"reason": "no_expected_sources"})

        expected = set(sample.expected_source_ids)
        top_k_chunks = sample.retrieved_chunks[: self.k]

        retrieved_ids: Set[str] = set()
        for r in top_k_chunks:
            retrieved_ids.add(r.chunk.chunk_id)
            retrieved_ids.add(r.chunk.document_id)
            if "source" in r.chunk.metadata:
                retrieved_ids.add(str(r.chunk.metadata["source"]))

        hit = bool(expected.intersection(retrieved_ids))
        return MetricResult(
            metric_name=self.metric_name,
            score=1.0 if hit else 0.0,
            details={"k": self.k, "hit": hit, "expected": list(expected)},
        )


class MRREvaluator(BaseEvaluator):
    """Calculates Reciprocal Rank @ K: 1 / rank of the first relevant document in top K."""

    def __init__(self, k: int = 5) -> None:
        self.k = k

    @property
    def metric_name(self) -> str:
        return f"mrr@{self.k}"

    def evaluate(self, sample: EvalSample) -> MetricResult:
        if not sample.expected_source_ids:
            return MetricResult(metric_name=self.metric_name, score=1.0, details={"reason": "no_expected_sources"})

        expected = set(sample.expected_source_ids)
        top_k_chunks = sample.retrieved_chunks[: self.k]

        for rank, r in enumerate(top_k_chunks, start=1):
            ids = {r.chunk.chunk_id, r.chunk.document_id}
            if "source" in r.chunk.metadata:
                ids.add(str(r.chunk.metadata["source"]))

            if expected.intersection(ids):
                return MetricResult(
                    metric_name=self.metric_name,
                    score=1.0 / rank,
                    details={"first_hit_rank": rank, "k": self.k},
                )

        return MetricResult(
            metric_name=self.metric_name,
            score=0.0,
            details={"first_hit_rank": None, "k": self.k},
        )


class PrecisionEvaluator(BaseEvaluator):
    """Calculates Precision @ K: fraction of top K retrieved chunks that are relevant."""

    def __init__(self, k: int = 3) -> None:
        self.k = k

    @property
    def metric_name(self) -> str:
        return f"precision@{self.k}"

    def evaluate(self, sample: EvalSample) -> MetricResult:
        if not sample.expected_source_ids:
            return MetricResult(metric_name=self.metric_name, score=1.0)

        expected = set(sample.expected_source_ids)
        top_k_chunks = sample.retrieved_chunks[: self.k]
        if not top_k_chunks:
            return MetricResult(metric_name=self.metric_name, score=0.0)

        relevant_count = 0
        for r in top_k_chunks:
            ids = {r.chunk.chunk_id, r.chunk.document_id}
            if "source" in r.chunk.metadata:
                ids.add(str(r.chunk.metadata["source"]))
            if expected.intersection(ids):
                relevant_count += 1

        score = relevant_count / min(len(top_k_chunks), self.k)
        return MetricResult(
            metric_name=self.metric_name,
            score=score,
            details={"relevant_count": relevant_count, "k": self.k},
        )


class RecallEvaluator(BaseEvaluator):
    """Calculates Recall @ K: fraction of all expected documents retrieved in top K."""

    def __init__(self, k: int = 5) -> None:
        self.k = k

    @property
    def metric_name(self) -> str:
        return f"recall@{self.k}"

    def evaluate(self, sample: EvalSample) -> MetricResult:
        if not sample.expected_source_ids:
            return MetricResult(metric_name=self.metric_name, score=1.0)

        expected = set(sample.expected_source_ids)
        top_k_chunks = sample.retrieved_chunks[: self.k]

        retrieved_ids: Set[str] = set()
        for r in top_k_chunks:
            retrieved_ids.add(r.chunk.chunk_id)
            retrieved_ids.add(r.chunk.document_id)
            if "source" in r.chunk.metadata:
                retrieved_ids.add(str(r.chunk.metadata["source"]))

        found_count = len(expected.intersection(retrieved_ids))
        score = found_count / len(expected)
        return MetricResult(
            metric_name=self.metric_name,
            score=score,
            details={"found": found_count, "total_expected": len(expected)},
        )
