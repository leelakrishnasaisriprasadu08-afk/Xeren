"""Unit tests for PerformanceEvaluator."""

from xeren.eval.performance import PerformanceEvaluator
from xeren.eval.types import EvalSample
from xeren.models.types import TokenUsage


def test_percentile_calculation() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    p50 = PerformanceEvaluator.calculate_percentile(values, 50)
    p90 = PerformanceEvaluator.calculate_percentile(values, 90)

    assert p50 == 30.0
    assert p90 == 46.0


def test_performance_batch_aggregation() -> None:
    samples = [
        EvalSample(
            sample_id="s1",
            query="q1",
            latency_ms=100.0,
            token_usage=TokenUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75),
        ),
        EvalSample(
            sample_id="s2",
            query="q2",
            latency_ms=200.0,
            token_usage=TokenUsage(prompt_tokens=70, completion_tokens=35, total_tokens=105),
        ),
    ]

    metrics = PerformanceEvaluator.evaluate_batch(samples)

    assert metrics["latency_mean_ms"] == 150.0
    assert metrics["latency_min_ms"] == 100.0
    assert metrics["latency_max_ms"] == 200.0
    assert metrics["avg_total_tokens"] == 90.0
    assert metrics["total_tokens_consumed"] == 180.0
