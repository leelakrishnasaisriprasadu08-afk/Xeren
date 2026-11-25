"""Public exports for the Xeren evaluation framework."""

from xeren.eval.base import BaseEvaluator
from xeren.eval.correctness import ExactMatchEvaluator, TokenF1Evaluator
from xeren.eval.grounding import GroundingEvaluator
from xeren.eval.performance import PerformanceEvaluator
from xeren.eval.retrieval_metrics import (
    HitRateEvaluator,
    MRREvaluator,
    PrecisionEvaluator,
    RecallEvaluator,
)
from xeren.eval.runner import BenchmarkRunner
from xeren.eval.types import (
    EvalSample,
    EvaluationReport,
    MetricResult,
    SampleEvaluation,
)

__all__ = [
    # Types
    "EvalSample",
    "MetricResult",
    "SampleEvaluation",
    "EvaluationReport",
    # Base
    "BaseEvaluator",
    # Evaluators
    "HitRateEvaluator",
    "MRREvaluator",
    "PrecisionEvaluator",
    "RecallEvaluator",
    "GroundingEvaluator",
    "TokenF1Evaluator",
    "ExactMatchEvaluator",
    "PerformanceEvaluator",
    # Runner
    "BenchmarkRunner",
]
