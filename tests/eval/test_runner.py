"""Unit tests for BenchmarkRunner and EvaluationReport."""

from xeren.eval.runner import BenchmarkRunner
from xeren.eval.types import EvalSample
from xeren.models.types import TokenUsage
from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.types import SearchResult


def test_benchmark_runner_full_run() -> None:
    c1 = DocumentChunk(chunk_id="c1", document_id="doc1", content="Python is high-level.", chunk_index=0)
    c2 = DocumentChunk(chunk_id="c2", document_id="doc2", content="Rust is safe and fast.", chunk_index=0)

    samples = [
        EvalSample(
            sample_id="s1",
            query="What is Python?",
            ground_truth_answer="Python is a high-level programming language.",
            expected_source_ids=["doc1"],
            retrieved_chunks=[SearchResult(chunk=c1, score=0.95)],
            generated_answer="Python is high-level.",
            latency_ms=120.0,
            token_usage=TokenUsage(prompt_tokens=40, completion_tokens=10, total_tokens=50),
        ),
        EvalSample(
            sample_id="s2",
            query="What is Rust?",
            ground_truth_answer="Rust is a systems language focused on memory safety.",
            expected_source_ids=["doc2"],
            retrieved_chunks=[SearchResult(chunk=c2, score=0.88)],
            generated_answer="Rust is safe and fast.",
            latency_ms=150.0,
            token_usage=TokenUsage(prompt_tokens=45, completion_tokens=12, total_tokens=57),
        ),
    ]

    runner = BenchmarkRunner()
    report = runner.evaluate_samples("Xeren RAG Baseline", samples, metadata={"model": "llama3.2"})

    assert report.benchmark_name == "Xeren RAG Baseline"
    assert report.total_samples == 2
    assert "hit_rate@1" in report.aggregate_metrics
    assert report.aggregate_metrics["hit_rate@1"] == 1.0
    assert "grounding_faithfulness" in report.aggregate_metrics
    assert report.aggregate_metrics["grounding_faithfulness"] >= 0.8
    assert "latency_mean_ms" in report.aggregate_metrics
    assert report.aggregate_metrics["latency_mean_ms"] == 135.0

    # Markdown export
    md = report.to_markdown()
    assert "# Evaluation Report: Xeren RAG Baseline" in md
    assert "| `hit_rate@1` | 1.0000 |" in md
    assert "| `latency_mean_ms` | 135.0000 |" in md
