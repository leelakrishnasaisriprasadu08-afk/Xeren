"""Unit tests for GroundingEvaluator."""

from xeren.eval.grounding import GroundingEvaluator
from xeren.eval.types import EvalSample
from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.types import SearchResult


def test_grounding_evaluator_high_faithfulness() -> None:
    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        content="Python was created by Guido van Rossum and released in 1991.",
        chunk_index=0,
    )
    sample = EvalSample(
        sample_id="s1",
        query="Who created Python?",
        retrieved_chunks=[SearchResult(chunk=chunk, score=0.95)],
        generated_answer="Python was created by Guido van Rossum in 1991.",
    )

    evaluator = GroundingEvaluator()
    res = evaluator.evaluate(sample)

    assert res.metric_name == "grounding_faithfulness"
    assert res.score >= 0.85
    assert res.details["token_grounding"] >= 0.85


def test_grounding_evaluator_hallucination() -> None:
    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        content="Quantum computing leverages qubits and superposition.",
        chunk_index=0,
    )
    sample = EvalSample(
        sample_id="s2",
        query="What is the weather today?",
        retrieved_chunks=[SearchResult(chunk=chunk, score=0.3)],
        generated_answer="It is sunny and 25 degrees Celsius outside in Madrid.",
    )

    evaluator = GroundingEvaluator()
    res = evaluator.evaluate(sample)

    assert res.score < 0.2
