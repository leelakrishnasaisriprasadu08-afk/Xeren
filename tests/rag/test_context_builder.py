"""Unit tests for ContextBuilder and citation formatting."""

import pytest

from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import ContextConfig
from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.types import SearchResult


@pytest.fixture
def sample_results() -> list[SearchResult]:
    c1 = DocumentChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        content="Artificial intelligence is transforming industries.",
        chunk_index=0,
        metadata={"source": "ai_overview.md", "title": "AI Overview", "header_path": "Introduction > Scope"},
    )
    c2 = DocumentChunk(
        chunk_id="chunk-2",
        document_id="doc-2",
        content="Neural networks model complex non-linear relationships.",
        chunk_index=0,
        metadata={"source": "dl_book.md", "title": "Deep Learning", "header_path": "Foundations"},
    )
    c3 = DocumentChunk(
        chunk_id="chunk-3",
        document_id="doc-3",
        content="Irrelevant noisy text snippet.",
        chunk_index=0,
        metadata={"source": "noise.txt"},
    )

    return [
        SearchResult(chunk=c1, score=0.95, retrieval_type="dense"),
        SearchResult(chunk=c2, score=0.85, retrieval_type="dense"),
        SearchResult(chunk=c3, score=0.20, retrieval_type="dense"),
    ]


def test_context_builder_basic(sample_results: list[SearchResult]) -> None:
    builder = ContextBuilder(ContextConfig(max_chunks=2))
    context = builder.build(sample_results)

    assert context.has_context is True
    assert len(context.selected_chunks) == 2
    assert len(context.citations) == 2

    # Check citations
    assert context.citations[0].citation_id == 1
    assert context.citations[0].source == "ai_overview.md"
    assert context.citations[0].header_path == "Introduction > Scope"

    assert context.citations[1].citation_id == 2
    assert context.citations[1].source == "dl_book.md"

    # Check formatted text structure
    assert "--- BEGIN GROUNDED CONTEXT ---" in context.formatted_text
    assert "[1] Source: ai_overview.md" in context.formatted_text
    assert "Artificial intelligence is transforming industries." in context.formatted_text
    assert "[2] Source: dl_book.md" in context.formatted_text
    assert "--- END GROUNDED CONTEXT ---" in context.formatted_text


def test_context_builder_min_score_filter(sample_results: list[SearchResult]) -> None:
    builder = ContextBuilder(ContextConfig(min_score_threshold=0.5, max_chunks=5))
    context = builder.build(sample_results)

    # Chunk 3 has score 0.20 < 0.5, so only 2 chunks selected
    assert len(context.selected_chunks) == 2
    assert all(c.score >= 0.5 for c in context.selected_chunks)


def test_context_builder_token_budget_enforcement(sample_results: list[SearchResult]) -> None:
    # Set a very tight token budget allowing only 1 chunk
    builder = ContextBuilder(ContextConfig(max_tokens=30, max_chunks=5))
    context = builder.build(sample_results)

    assert len(context.selected_chunks) == 1
    assert context.citations[0].chunk_id == "chunk-1"


def test_context_builder_empty_results() -> None:
    builder = ContextBuilder()
    context = builder.build([])

    assert context.has_context is False
    assert context.formatted_text == ""
    assert context.selected_chunks == []
    assert context.citations == []
