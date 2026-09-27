"""Performance and resource evaluation metrics: latency percentiles and token accounting."""

import math
from typing import Dict, List

from xeren.eval.types import EvalSample


class PerformanceEvaluator:
    """Computes latency percentiles and token consumption aggregates over dataset runs."""

    @staticmethod
    def calculate_percentile(values: List[float], percentile: float) -> float:
        """Calculate the p-th percentile of a sorted list of numbers."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        index = (percentile / 100.0) * (len(sorted_vals) - 1)
        lower = math.floor(index)
        upper = math.ceil(index)
        if lower == upper:
            return float(sorted_vals[int(index)])
        weight = index - lower
        return float(sorted_vals[lower] * (1.0 - weight) + sorted_vals[upper] * weight)

    @classmethod
    def evaluate_batch(cls, samples: List[EvalSample]) -> Dict[str, float]:
        """Aggregate performance and token metrics across a list of evaluation samples."""
        latencies = [s.latency_ms for s in samples if s.latency_ms is not None]
        prompt_tokens = [s.token_usage.prompt_tokens for s in samples if s.token_usage]
        completion_tokens = [s.token_usage.completion_tokens for s in samples if s.token_usage]
        total_tokens = [s.token_usage.total_tokens for s in samples if s.token_usage]

        metrics: Dict[str, float] = {}

        if latencies:
            metrics["latency_mean_ms"] = round(sum(latencies) / len(latencies), 2)
            metrics["latency_min_ms"] = round(min(latencies), 2)
            metrics["latency_max_ms"] = round(max(latencies), 2)
            metrics["latency_p50_ms"] = round(cls.calculate_percentile(latencies, 50), 2)
            metrics["latency_p90_ms"] = round(cls.calculate_percentile(latencies, 90), 2)
            metrics["latency_p95_ms"] = round(cls.calculate_percentile(latencies, 95), 2)

        if total_tokens:
            metrics["avg_prompt_tokens"] = round(sum(prompt_tokens) / len(prompt_tokens), 2)
            metrics["avg_completion_tokens"] = round(sum(completion_tokens) / len(completion_tokens), 2)
            metrics["avg_total_tokens"] = round(sum(total_tokens) / len(total_tokens), 2)
            metrics["total_tokens_consumed"] = float(sum(total_tokens))

        return metrics
