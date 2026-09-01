"""Grounding and faithfulness evaluation metrics."""

import re
from typing import List, Set

from xeren.eval.base import BaseEvaluator
from xeren.eval.types import EvalSample, MetricResult


class GroundingEvaluator(BaseEvaluator):
    """Measures the grounding and faithfulness of generated answers against retrieved context."""

    def __init__(self, min_ngram_match: int = 2) -> None:
        self.min_ngram_match = min_ngram_match

    @property
    def metric_name(self) -> str:
        return "grounding_faithfulness"

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _extract_ngrams(self, tokens: List[str], n: int) -> Set[str]:
        return {
            " ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)
        }

    def evaluate(self, sample: EvalSample) -> MetricResult:
        if not sample.generated_answer:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                details={"reason": "no_generated_answer"},
            )

        # Aggregate context from retrieved chunks
        context_text = " ".join(r.chunk.content for r in sample.retrieved_chunks)
        if not context_text:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                details={"reason": "empty_context"},
            )

        answer_tokens = self._tokenize(sample.generated_answer)
        context_tokens = self._tokenize(context_text)

        if not answer_tokens:
            return MetricResult(metric_name=self.metric_name, score=1.0)

        # 1. Token overlap
        ans_set = set(answer_tokens)
        ctx_set = set(context_tokens)
        overlap_tokens = ans_set.intersection(ctx_set)
        token_grounding = len(overlap_tokens) / len(ans_set) if ans_set else 0.0

        # 2. N-gram phrase overlap (if answer has enough tokens)
        if len(answer_tokens) >= self.min_ngram_match:
            ans_ngrams = self._extract_ngrams(answer_tokens, self.min_ngram_match)
            ctx_ngrams = self._extract_ngrams(context_tokens, self.min_ngram_match)
            ngram_overlap = len(ans_ngrams.intersection(ctx_ngrams)) / len(ans_ngrams) if ans_ngrams else 0.0
        else:
            ngram_overlap = token_grounding

        # Weighted combination: 40% token overlap + 60% n-gram sequence match
        composite_score = round(0.4 * token_grounding + 0.6 * ngram_overlap, 4)

        return MetricResult(
            metric_name=self.metric_name,
            score=composite_score,
            details={
                "token_grounding": round(token_grounding, 4),
                "ngram_grounding": round(ngram_overlap, 4),
                "answer_tokens": len(answer_tokens),
                "context_tokens": len(context_tokens),
            },
        )
