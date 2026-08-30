"""Unit tests for answer correctness metrics."""

import pytest

from xeren.eval.correctness import ExactMatchEvaluator, TokenF1Evaluator
from xeren.eval.types import EvalSample


def test_exact_match_evaluator() -> None:
    evaluator = ExactMatchEvaluator()

    sample_match = EvalSample(
        sample_id="1",
        query="q",
        ground_truth_answer="Paris, France",
        generated_answer="paris france",
    )
    res_match = evaluator.evaluate(sample_match)
    assert res_match.score == 1.0

    sample_diff = EvalSample(
        sample_id="2",
        query="q",
        ground_truth_answer="Berlin",
        generated_answer="London",
    )
    res_diff = evaluator.evaluate(sample_diff)
    assert res_diff.score == 0.0


def test_token_f1_evaluator() -> None:
    evaluator = TokenF1Evaluator()

    # Exact match -> F1 = 1.0
    s1 = EvalSample(sample_id="1", query="q", ground_truth_answer="The quick brown fox", generated_answer="the quick brown fox")
    assert evaluator.evaluate(s1).score == 1.0

    # Partial match
    # Gold: [quick, brown, fox] (3), Pred: [quick, red, fox] (3), Common: [quick, fox] (2)
    # Precision = 2/3, Recall = 2/3 -> F1 = 2/3 = ~0.6667
    s2 = EvalSample(sample_id="2", query="q", ground_truth_answer="quick brown fox", generated_answer="quick red fox")
    res2 = evaluator.evaluate(s2)
    assert res2.score == pytest.approx(0.6667, abs=1e-3)

    # Zero overlap -> F1 = 0.0
    s3 = EvalSample(sample_id="3", query="q", ground_truth_answer="apple orange", generated_answer="banana grape")
    assert evaluator.evaluate(s3).score == 0.0
