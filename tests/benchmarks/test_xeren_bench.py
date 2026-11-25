"""Xeren-Bench: Empirical Student & Engineering Evaluation Harness.

Evaluates Xeren's ability to deconstruct real-world student engineering problems,
execute solutions within an isolated sandbox, and distill causal lessons.
"""

from dataclasses import dataclass
from typing import List
import pytest


@dataclass
class BenchmarkTask:
    task_id: str
    category: str
    prompt: str
    expected_exit_code: int
    validation_keywords: List[str]


BENCHMARK_SUITE: List[BenchmarkTask] = [
    BenchmarkTask(
        task_id="student_bench_01",
        category="algorithm_optimization",
        prompt="Optimize O(2^N) recursive Fibonacci to O(N) dynamic programming.",
        expected_exit_code=0,
        validation_keywords=["dynamic_programming", "memoization", "linear_time"],
    ),
    BenchmarkTask(
        task_id="student_bench_02",
        category="schema_validation",
        prompt="Detect syntax and schema defects in an unescaped JSON configuration payload.",
        expected_exit_code=0,
        validation_keywords=["json_schema", "ast_validation", "syntax_error"],
    ),
]


def test_benchmark_suite_registration():
    """Verify benchmark tasks are properly structured and loadable."""
    assert len(BENCHMARK_SUITE) >= 2
    for task in BENCHMARK_SUITE:
        assert task.task_id.startswith("student_bench_")
        assert len(task.validation_keywords) > 0
