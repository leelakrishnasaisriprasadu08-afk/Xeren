"""Tests for KnowledgePlugin schemas and validation."""

import pytest
from pydantic import ValidationError

from xeren.plugins.knowledge.schemas import (
    KnowledgeInput,
    KnowledgeOperation,
    KnowledgeResult,
    RetrievalMode,
)
from xeren.rag.context.types import Citation, GroundedContext
from xeren.rag.document import Document, DocumentChunk
from xeren.rag.retrieval.types import SearchResult


def test_knowledge_input_valid_query():
    """Verify valid query input builds successfully."""
    inp = KnowledgeInput(query="What is transformer architecture?", top_k=10)
    assert inp.query == "What is transformer architecture?"
    assert inp.operation == KnowledgeOperation.QUERY
    assert inp.top_k == 10
    assert inp.top_n == 5
    assert inp.retrieval_mode == RetrievalMode.HYBRID
    assert inp.include_context is True
    assert inp.include_provenance is True


def test_knowledge_input_empty_query_raises():
    """Verify empty or whitespace query raises ValidationError in QUERY mode."""
    with pytest.raises(ValidationError) as exc_info:
        KnowledgeInput(query="")
    assert "requires a non-empty 'query'" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        KnowledgeInput(query="   ")
    assert "requires a non-empty 'query'" in str(exc_info.value)


def test_knowledge_input_valid_ingest_texts():
    """Verify valid ingest input with raw texts."""
    inp = KnowledgeInput(
        operation=KnowledgeOperation.INGEST,
        texts=["Doc 1 text", "Doc 2 text"],
        source="unit_test",
    )
    assert inp.operation == KnowledgeOperation.INGEST
    assert inp.texts == ["Doc 1 text", "Doc 2 text"]
    assert inp.source == "unit_test"


def test_knowledge_input_valid_ingest_documents():
    """Verify valid ingest input with Document instances."""
    doc = Document.from_text(text="Sample document content", source="unit_test", doc_id="doc-1")
    inp = KnowledgeInput(
        operation=KnowledgeOperation.INGEST,
        documents=[doc],
    )
    assert inp.operation == KnowledgeOperation.INGEST
    assert inp.documents is not None and len(inp.documents) == 1


def test_knowledge_input_ingest_missing_content_raises():
    """Verify ingest mode without texts or documents raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        KnowledgeInput(operation=KnowledgeOperation.INGEST)
    assert "requires either 'documents' or 'texts'" in str(exc_info.value)


def test_knowledge_input_boundary_validation():
    """Verify top_k and min_score field constraints."""
    with pytest.raises(ValidationError):
        KnowledgeInput(query="test", top_k=0)

    with pytest.raises(ValidationError):
        KnowledgeInput(query="test", top_k=101)

    with pytest.raises(ValidationError):
        KnowledgeInput(query="test", min_score=-0.1)

    with pytest.raises(ValidationError):
        KnowledgeInput(query="test", min_score=1.5)


def test_knowledge_result_structure():
    """Verify KnowledgeResult structured attributes and serialization."""
    chunk = DocumentChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        content="Xeren is an AI platform.",
        chunk_index=0,
        metadata={"source": "whitepaper.pdf"},
    )
    search_res = SearchResult(chunk=chunk, score=0.92)
    citation = Citation(
        citation_id=1,
        source="whitepaper.pdf",
        chunk_id="chunk-1",
    )
    context = GroundedContext(
        formatted_text="[1] Xeren is an AI platform.",
        citations=[citation],
        estimated_tokens=10,
        total_characters=28,
        has_context=True,
    )

    res = KnowledgeResult(
        operation=KnowledgeOperation.QUERY,
        query="What is Xeren?",
        retrieved_chunks=[chunk],
        ranked_results=[search_res],
        context=context,
        provenance=[citation],
        retrieval_scores={"chunk-1": 0.92},
        knowledge_gaps=[],
        execution_stats={"latency_ms": 12.5},
        success=True,
    )

    assert res.operation == KnowledgeOperation.QUERY
    assert res.query == "What is Xeren?"
    assert len(res.retrieved_chunks) == 1
    assert len(res.ranked_results) == 1
    assert res.context is not None
    assert len(res.provenance) == 1
    assert res.retrieval_scores["chunk-1"] == 0.92
    assert res.success is True

    # Test serialization
    dumped = res.model_dump()
    assert dumped["operation"] == "query"
    assert dumped["query"] == "What is Xeren?"
    assert dumped["success"] is True
