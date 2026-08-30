"""End-to-end integration tests for RAGQueryEngine."""

import pytest

from xeren.rag.chunkers.markdown_header import MarkdownHeaderChunker
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import ContextConfig
from xeren.rag.document import Document
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.rerankers.threshold import ScoreThresholdReranker
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.stores.memory_store import InMemoryVectorStore


@pytest.fixture
def setup_rag_engine() -> RAGQueryEngine:
    # 1. Setup embedding and store
    embedder = MockEmbeddingModel(dimension=64)
    store = InMemoryVectorStore()

    # 2. Ingest structured document
    doc_text = """# Operating Systems

Overview of kernel architectures and processes.

## Linux Kernel

Linux is a monolithic Unix-like kernel managing hardware resources.

## Windows Architecture

Windows uses a hybrid kernel architecture with executive subsystems.

## Noise Section

Unrelated miscellaneous trivia.
"""
    doc = Document.from_text(doc_text, source="/docs/os.md", title="OS Handbook")
    chunker = MarkdownHeaderChunker(max_chunk_size=500)
    chunks = chunker.chunk(doc)

    embedded = embedder.embed_chunks(chunks)
    store.add_chunks(embedded)

    # 3. Build query engine with retriever, reranker (threshold filter), and context builder
    retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
    reranker = ScoreThresholdReranker(min_score=-1.0)
    context_builder = ContextBuilder(
        ContextConfig(max_chunks=3, min_score_threshold=-1.0, include_header_metadata=True)
    )

    return RAGQueryEngine(
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
    )


def test_rag_query_engine_sync(setup_rag_engine: RAGQueryEngine) -> None:
    engine = setup_rag_engine
    context = engine.query("Linux kernel architecture", top_k=5, top_n=2)

    assert context.has_context is True
    assert len(context.selected_chunks) >= 1
    assert len(context.citations) >= 1

    assert "--- BEGIN GROUNDED CONTEXT ---" in context.formatted_text
    assert "--- END GROUNDED CONTEXT ---" in context.formatted_text
    assert "Source: /docs/os.md" in context.formatted_text
    assert context.citations[0].source == "/docs/os.md"


@pytest.mark.asyncio
async def test_rag_query_engine_async(setup_rag_engine: RAGQueryEngine) -> None:
    engine = setup_rag_engine
    context = await engine.aquery("Windows hybrid kernel", top_k=5, top_n=2)

    assert context.has_context is True
    assert len(context.selected_chunks) >= 1
    assert context.total_characters > 0
    assert context.estimated_tokens > 0


def test_rag_query_engine_empty_query(setup_rag_engine: RAGQueryEngine) -> None:
    engine = setup_rag_engine
    context = engine.query("", top_k=5)

    assert context.has_context is False
    assert context.formatted_text == ""
    assert context.selected_chunks == []
