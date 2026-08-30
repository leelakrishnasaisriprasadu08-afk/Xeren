"""Unit tests for Dense, Keyword, and Hybrid retrievers."""

import pytest

from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.hybrid import HybridRetriever
from xeren.rag.retrieval.keyword import KeywordRetriever
from xeren.rag.stores.memory_store import InMemoryVectorStore


@pytest.fixture
def populated_store_and_chunks() -> tuple[InMemoryVectorStore, MockEmbeddingModel, list[DocumentChunk]]:
    model = MockEmbeddingModel(dimension=64)
    store = InMemoryVectorStore()

    c1 = DocumentChunk(
        chunk_id="chunk-python",
        document_id="doc-1",
        content="Python is an interpreted, high-level, general-purpose programming language.",
        chunk_index=0,
        metadata={"topic": "python", "language": "en"},
    )
    c2 = DocumentChunk(
        chunk_id="chunk-rust",
        document_id="doc-2",
        content="Rust is a systems programming language focused on memory safety and speed.",
        chunk_index=0,
        metadata={"topic": "rust", "language": "en"},
    )
    c3 = DocumentChunk(
        chunk_id="chunk-ai",
        document_id="doc-3",
        content="Machine learning neural networks algorithms and gradient descent optimization.",
        chunk_index=0,
        metadata={"topic": "ai", "language": "en"},
    )

    chunks = [c1, c2, c3]
    embedded = model.embed_chunks(chunks)
    store.add_chunks(embedded)

    return store, model, chunks


def test_dense_retriever(populated_store_and_chunks: tuple) -> None:
    store, model, _ = populated_store_and_chunks
    retriever = DenseRetriever(embedding_model=model, vector_store=store)

    results = retriever.retrieve("Python programming", top_k=2)
    assert len(results) >= 1
    assert results[0].retrieval_type == "dense"
    assert results[0].score > 0.0


def test_keyword_retriever(populated_store_and_chunks: tuple) -> None:
    _, _, chunks = populated_store_and_chunks
    retriever = KeywordRetriever(chunks_provider=lambda: chunks)

    results = retriever.retrieve("Rust systems memory safety", top_k=2)
    assert len(results) >= 1
    assert results[0].chunk.chunk_id == "chunk-rust"
    assert results[0].retrieval_type == "sparse"


def test_keyword_retriever_with_filter(populated_store_and_chunks: tuple) -> None:
    _, _, chunks = populated_store_and_chunks
    retriever = KeywordRetriever(chunks_provider=lambda: chunks)

    # Search keyword "programming" but filter to topic == "python"
    flt = MetadataFilter.eq("topic", "python")
    results = retriever.retrieve("programming", top_k=5, filter=flt)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "chunk-python"


def test_hybrid_retriever_rrf(populated_store_and_chunks: tuple) -> None:
    store, model, chunks = populated_store_and_chunks
    dense = DenseRetriever(embedding_model=model, vector_store=store)
    sparse = KeywordRetriever(chunks_provider=lambda: chunks)

    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse, fusion_mode="rrf")
    results = hybrid.retrieve("Python programming language", top_k=3)

    assert len(results) >= 1
    assert results[0].retrieval_type == "hybrid"
    # Python chunk should be ranked first due to both semantic and exact token overlap
    assert results[0].chunk.chunk_id == "chunk-python"


@pytest.mark.asyncio
async def test_hybrid_retriever_async(populated_store_and_chunks: tuple) -> None:
    store, model, chunks = populated_store_and_chunks
    dense = DenseRetriever(embedding_model=model, vector_store=store)
    sparse = KeywordRetriever(chunks_provider=lambda: chunks)

    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse, fusion_mode="linear")
    results = await hybrid.aretrieve("neural networks", top_k=2)

    assert len(results) >= 1
    assert results[0].retrieval_type == "hybrid"
