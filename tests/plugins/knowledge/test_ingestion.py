"""Tests for KnowledgePlugin document and text ingestion pipeline integration."""

import pytest

from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.schemas import (
    KnowledgeInput,
    KnowledgeOperation,
    KnowledgeResult,
)
from xeren.plugins.knowledge.tools.ingestion import KnowledgeIngestionTool
from xeren.rag.document import Document


def test_ingest_raw_texts():
    """Verify ingesting raw texts indexes into both vector store and keyword retriever."""
    plugin = KnowledgePlugin()
    result = plugin.ingest(
        texts=[
            "Xeren features autonomous agentic workflows and modular plugin orchestration.",
            "Retrieval Augmented Generation in Xeren uses hybrid search combining dense vectors and BM25.",
        ],
        source="doc_test_1",
    )

    assert result.operation == KnowledgeOperation.INGEST
    assert result.success is True
    assert len(result.inserted_chunk_ids) == 2
    assert plugin.workflow.vector_store.count() == 2

    # Verify keyword retriever synchronization
    bm25_hits = plugin.workflow.keyword_retriever.retrieve("orchestration", top_k=2)
    assert len(bm25_hits) >= 1
    assert "autonomous agentic workflows" in bm25_hits[0].chunk.content


def test_ingest_documents():
    """Verify ingesting Document objects preserves document IDs and metadata."""
    plugin = KnowledgePlugin()
    doc1 = Document.from_text(
        text="Xeren Core integrates model providers, plugin manager, and memory stores.",
        source="arch_overview.md",
        doc_id="arch_overview",
        extra={"category": "architecture", "author": "core_team"},
    )
    doc2 = Document.from_text(
        text="Evaluation module calculates precision at k and reciprocal rank for retrieval.",
        source="eval_spec.md",
        doc_id="eval_spec",
        extra={"category": "eval", "author": "eval_team"},
    )

    result = plugin.ingest(documents=[doc1, doc2])
    assert result.operation == KnowledgeOperation.INGEST
    assert len(result.inserted_chunk_ids) == 2
    assert plugin.workflow.vector_store.count() == 2

    # Verify vector store search returns matches
    results = plugin.workflow.dense_retriever.retrieve("architecture", top_k=2)
    assert len(results) > 0


def test_ingest_batch_texts_and_documents():
    """Verify batch ingestion of both documents and raw text strings."""
    plugin = KnowledgePlugin()
    doc = Document.from_text(
        text="Document A text discussing python type systems.",
        source="doc_a.txt",
        doc_id="doc_a",
    )
    result = plugin.ingest(
        texts=["Raw text B discussing asynchronous execution."],
        documents=[doc],
        source="mixed_ingest",
    )

    assert len(result.inserted_chunk_ids) == 2
    assert plugin.workflow.vector_store.count() == 2


def test_ingestion_tool_direct():
    """Verify KnowledgeIngestionTool unit behaviors."""
    plugin = KnowledgePlugin()
    tool = KnowledgeIngestionTool(pipeline=plugin.workflow.ingestion_pipeline)

    chunk_ids = tool.ingest_text("Direct tool ingestion text snippet.", source="tool_test")
    assert len(chunk_ids) >= 1
    assert plugin.workflow.vector_store.count() >= 1


@pytest.mark.asyncio
async def test_async_ingest():
    """Verify asynchronous ingestion via plugin.aexecute."""
    plugin = KnowledgePlugin()
    inp = KnowledgeInput(
        operation=KnowledgeOperation.INGEST,
        texts=["Async indexed text content."],
        source="async_test",
    )
    exec_res = await plugin.aexecute(inp)
    assert exec_res.success is True
    assert isinstance(exec_res.output, KnowledgeResult)
    assert len(exec_res.output.inserted_chunk_ids) == 1
    assert plugin.workflow.vector_store.count() == 1

