"""Answer correctness evaluation metrics: Exact Match, Token F1, and Precision/Recall."""

import re
from typing import Counter, List

from xeren.eval.base import BaseEvaluator
from xeren.eval.types import EvalSample, MetricResult


class TokenF1Evaluator(BaseEvaluator):
    """Calculates Token-level Precision, Recall, and F1 score against reference answer."""

    @property
    def metric_name(self) -> str:
        return "token_f1"

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def evaluate(self, sample: EvalSample) -> MetricResult:
        if not sample.ground_truth_answer:
            return MetricResult(metric_name=self.metric_name, score=1.0, details={"reason": "no_ground_truth"})
        if not sample.generated_answer:
            return MetricResult(metric_name=self.metric_name, score=0.0, details={"reason": "no_generated_answer"})

        pred_tokens = self._tokenize(sample.generated_answer)
        gold_tokens = self._tokenize(sample.ground_truth_answer)

        if not pred_tokens or not gold_tokens:
            score = 1.0 if pred_tokens == gold_tokens else 0.0
            return MetricResult(metric_name=self.metric_name, score=score)

        pred_counts = Counter(pred_tokens)
        gold_counts = Counter(gold_tokens)

        # Count common tokens
        common = sum((pred_counts & gold_counts).values())
        if common == 0:
            return MetricResult(metric_name=self.metric_name, score=0.0, details={"precision": 0.0, "recall": 0.0})

        precision = common / len(pred_tokens)
        recall = common / len(gold_tokens)
        f1 = (2 * precision * recall) / (precision + recall)

        return MetricResult(
            metric_name=self.metric_name,
            score=round(f1, 4),
            details={
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "common_tokens": common,
            },
        )


class ExactMatchEvaluator(BaseEvaluator):
    """Calculates normalized exact match (1.0 or 0.0)."""

    @property
    def metric_name(self) -> str:
        return "exact_match"

    def _normalize(self, text: str) -> str:
        tokens = re.findall(r"\w+", text.lower())
        return " ".join(tokens)

    def evaluate(self, sample: EvalSample) -> MetricResult:
        if not sample.ground_truth_answer:
            return MetricResult(metric_name=self.metric_name, score=1.0, details={"reason": "no_ground_truth"})
        if not sample.generated_answer:
            return MetricResult(metric_name=self.metric_name, score=0.0)

        match = self._normalize(sample.generated_answer) == self._normalize(sample.ground_truth_answer)
        return MetricResult(
            metric_name=self.metric_name,
            score=1.0 if match else 0.0,
            details={"match": match},
        )
