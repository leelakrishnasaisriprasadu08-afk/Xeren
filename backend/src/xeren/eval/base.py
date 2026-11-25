"""Abstract base evaluator interface for Xeren."""

import asyncio
from abc import ABC, abstractmethod

from xeren.eval.types import EvalSample, MetricResult


class BaseEvaluator(ABC):
    """Abstract base class for all metric evaluators."""

    @property
    @abstractmethod
    def metric_name(self) -> str:
        """Unique identifier for this metric."""
        pass

    @abstractmethod
    def evaluate(self, sample: EvalSample) -> MetricResult:
        """Evaluate a single test sample synchronously."""
        pass

    async def aevaluate(self, sample: EvalSample) -> MetricResult:
        """Evaluate a single test sample asynchronously."""
        return await asyncio.to_thread(self.evaluate, sample)
