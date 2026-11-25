"""Benchmark runner orchestrating full evaluation runs over datasets."""

from typing import Any, Dict, List, Optional

from xeren.eval.base import BaseEvaluator
from xeren.eval.correctness import ExactMatchEvaluator, TokenF1Evaluator
from xeren.eval.grounding import GroundingEvaluator
from xeren.eval.performance import PerformanceEvaluator
from xeren.eval.retrieval_metrics import HitRateEvaluator, MRREvaluator, PrecisionEvaluator, RecallEvaluator
from xeren.eval.types import EvalSample, EvaluationReport, MetricResult, SampleEvaluation


class BenchmarkRunner:
    """Orchestrates comprehensive benchmark evaluations over test datasets."""

    def __init__(self, evaluators: Optional[List[BaseEvaluator]] = None) -> None:
        self.evaluators = evaluators if evaluators is not None else self._default_evaluators()

    def _default_evaluators(self) -> List[BaseEvaluator]:
        return [
            HitRateEvaluator(k=1),
            HitRateEvaluator(k=3),
            MRREvaluator(k=5),
            PrecisionEvaluator(k=3),
            RecallEvaluator(k=3),
            GroundingEvaluator(),
            TokenF1Evaluator(),
            ExactMatchEvaluator(),
        ]

    def evaluate_sample(self, sample: EvalSample) -> SampleEvaluation:
        """Evaluate a single test sample across all registered evaluators."""
        metric_results: Dict[str, MetricResult] = {}
        for evaluator in self.evaluators:
            res = evaluator.evaluate(sample)
            metric_results[evaluator.metric_name] = res
        return SampleEvaluation(sample_id=sample.sample_id, metrics=metric_results)

    def evaluate_samples(
        self,
        benchmark_name: str,
        samples: List[EvalSample],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationReport:
        """Run full evaluation suite across all samples and calculate dataset summary aggregates."""
        if not samples:
            return EvaluationReport(
                benchmark_name=benchmark_name,
                total_samples=0,
                aggregate_metrics={},
                sample_evaluations=[],
                summary_metadata=metadata or {},
            )

        sample_evaluations: List[SampleEvaluation] = []
        metric_accumulators: Dict[str, List[float]] = {}

        for sample in samples:
            sample_eval = self.evaluate_sample(sample)
            sample_evaluations.append(sample_eval)

            for metric_name, result in sample_eval.metrics.items():
                if metric_name not in metric_accumulators:
                    metric_accumulators[metric_name] = []
                metric_accumulators[metric_name].append(result.score)

        # Calculate mean scores
        aggregate_metrics: Dict[str, float] = {}
        for metric_name, scores in metric_accumulators.items():
            aggregate_metrics[metric_name] = round(sum(scores) / len(scores), 4)

        # Calculate latency and token aggregates
        perf_metrics = PerformanceEvaluator.evaluate_batch(samples)
        aggregate_metrics.update(perf_metrics)

        return EvaluationReport(
            benchmark_name=benchmark_name,
            total_samples=len(samples),
            aggregate_metrics=aggregate_metrics,
            sample_evaluations=sample_evaluations,
            summary_metadata=metadata or {},
        )
