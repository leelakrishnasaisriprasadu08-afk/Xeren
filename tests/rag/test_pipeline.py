"""Integration tests for IngestionPipeline."""

from pathlib import Path
import pytest

from xeren.rag.chunkers.recursive import RecursiveTextChunker
from xeren.rag.document import Document
from xeren.rag.normalizers.text_normalizer import TextNormalizer
from xeren.rag.pipeline import IngestionPipeline


def test_pipeline_process_text() -> None:
    pipeline = IngestionPipeline()
    text = "Line 1.\r\n\r\nLine 2.\r\n\r\nLine 3."
    chunks = pipeline.process_text(text, source="memory", title="Demo")

    assert len(chunks) >= 1
    assert chunks[0].metadata["source"] == "memory"
    assert chunks[0].metadata["title"] == "Demo"
    assert "\r" not in chunks[0].content


@pytest.mark.asyncio
async def test_pipeline_aprocess_text() -> None:
    pipeline = IngestionPipeline()
    text = "Async text ingestion test."
    chunks = await pipeline.aprocess_text(text, source="async_src")

    assert len(chunks) == 1
    assert chunks[0].content == "Async text ingestion test."


def test_pipeline_process_file(tmp_path: Path) -> None:
    pipeline = IngestionPipeline()
    doc_path = tmp_path / "guide.md"
    doc_path.write_text(
        "---\ntitle: Guide\n---\n# Chapter 1\n\nContent for chapter 1 goes here.\n",
        encoding="utf-8",
    )

    chunks = pipeline.process_file(doc_path)
    assert len(chunks) >= 1
    assert chunks[0].metadata["title"] == "Guide"
    assert "Content for chapter 1 goes here." in chunks[0].content


def test_pipeline_process_directory(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "doc1.txt").write_text("Hello text file 1", encoding="utf-8")
    (tmp_path / "sub" / "doc2.md").write_text("# Hello markdown file 2", encoding="utf-8")

    pipeline = IngestionPipeline()
    chunks = pipeline.process_directory(tmp_path)

    assert len(chunks) == 2
    contents = {c.content for c in chunks}
    assert any("Hello text file 1" in c for c in contents)
    assert any("# Hello markdown file 2" in c for c in contents)


def test_pipeline_index_text_and_search() -> None:
    from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
    from xeren.rag.retrieval.dense import DenseRetriever
    from xeren.rag.stores.memory_store import InMemoryVectorStore

    embedder = MockEmbeddingModel(dimension=64)
    store = InMemoryVectorStore()
    pipeline = IngestionPipeline(embedding_model=embedder, vector_store=store)

    inserted_ids = pipeline.index_text(
        "Xeren is an AI system that unifies models, memory, and grounded retrieval.",
        source="spec.txt",
        title="Xeren Overview",
    )

    assert len(inserted_ids) >= 1
    assert store.count() == len(inserted_ids)

    # Validate that indexed documents are immediately retrievable
    retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
    results = retriever.retrieve("Xeren models and retrieval", top_k=2)
    assert len(results) >= 1
    assert "Xeren is an AI system" in results[0].chunk.content
    assert results[0].chunk.metadata["source"] == "spec.txt"


@pytest.mark.asyncio
async def test_pipeline_aindex_file_and_search(tmp_path: Path) -> None:
    from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
    from xeren.rag.retrieval.dense import DenseRetriever
    from xeren.rag.stores.memory_store import InMemoryVectorStore

    embedder = MockEmbeddingModel(dimension=64)
    store = InMemoryVectorStore()
    pipeline = IngestionPipeline(embedding_model=embedder, vector_store=store)

    doc_path = tmp_path / "architecture.md"
    doc_path.write_text(
        "---\ntitle: Architecture\n---\n# Security\n\nSecurity authorizes all tool execution.\n",
        encoding="utf-8",
    )

    inserted_ids = await pipeline.aindex_file(doc_path)
    assert len(inserted_ids) >= 1
    assert store.count() == len(inserted_ids)

    retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
    results = await retriever.aretrieve("security tool execution", top_k=2)
    assert len(results) >= 1
    assert "Security authorizes all tool execution" in results[0].chunk.content


def test_pipeline_index_missing_configuration() -> None:
    from xeren.rag.errors import PipelineExecutionError

    pipeline = IngestionPipeline()  # No embedder or store configured
    with pytest.raises(PipelineExecutionError, match="No embedding model configured"):
        pipeline.index_text("Sample text")


# ---------------------------------------------------------------------------
# Index synchronization: vector store and BM25 must stay in sync
# ---------------------------------------------------------------------------

def test_pipeline_vector_and_bm25_stay_in_sync() -> None:
    """After index_text(), the BM25 index must contain the same chunks as the vector store."""
    from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
    from xeren.rag.retrieval.keyword import KeywordRetriever
    from xeren.rag.stores.memory_store import InMemoryVectorStore

    embedder = MockEmbeddingModel(dimension=64)
    store = InMemoryVectorStore()
    kw_retriever = KeywordRetriever()  # empty index — no provider

    pipeline = IngestionPipeline(
        embedding_model=embedder,
        vector_store=store,
        keyword_retriever=kw_retriever,
    )

    # BM25 index must be empty before any indexing.
    assert kw_retriever._index.num_chunks == 0

    pipeline.index_text(
        "Xeren is an AI system that unifies models memory and grounded retrieval.",
        source="spec.txt",
        title="Xeren Overview",
    )

    # Both indexes must now have the same number of chunks.
    assert store.count() == kw_retriever._index.num_chunks
    assert kw_retriever._index.num_chunks >= 1

    # BM25 index must return the indexed chunk for a matching keyword query.
    results = kw_retriever.retrieve("Xeren retrieval memory", top_k=3)
    assert len(results) >= 1
    assert results[0].chunk.metadata["source"] == "spec.txt"


@pytest.mark.asyncio
async def test_pipeline_async_vector_and_bm25_stay_in_sync(tmp_path: Path) -> None:
    """After aindex_file(), the BM25 index must reflect the same chunks as the vector store."""
    from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
    from xeren.rag.retrieval.keyword import KeywordRetriever
    from xeren.rag.stores.memory_store import InMemoryVectorStore

    embedder = MockEmbeddingModel(dimension=64)
    store = InMemoryVectorStore()
    kw_retriever = KeywordRetriever()

    pipeline = IngestionPipeline(
        embedding_model=embedder,
        vector_store=store,
        keyword_retriever=kw_retriever,
    )

    doc_path = tmp_path / "security.md"
    doc_path.write_text(
        "---\ntitle: Security\n---\n# Security\n\nSecurity authorizes all tool execution.\n",
        encoding="utf-8",
    )

    inserted_ids = await pipeline.aindex_file(doc_path)

    # Both indexes must have the same chunk count.
    assert store.count() == len(inserted_ids)
    assert kw_retriever._index.num_chunks == len(inserted_ids)

    # BM25 must find the right chunk by keyword.
    results = kw_retriever.retrieve("security tool execution", top_k=2)
    assert len(results) >= 1
    assert "Security authorizes all tool execution" in results[0].chunk.content
