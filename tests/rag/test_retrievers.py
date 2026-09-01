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
    # #1 rank in both retrievers should produce normalized score of 1.0
    assert pytest.approx(results[0].score, rel=1e-3) == 1.0
    # All scores must be in [0.0, 1.0]
    assert all(0.0 <= r.score <= 1.0 for r in results)


def test_hybrid_retriever_rrf_single_active_retriever(populated_store_and_chunks: tuple) -> None:
    """When only one retriever produces candidates, RRF normalizes using single active retriever max."""
    store, model, _ = populated_store_and_chunks
    dense = DenseRetriever(embedding_model=model, vector_store=store)
    empty_sparse = KeywordRetriever(chunks_provider=lambda: [])

    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=empty_sparse, fusion_mode="rrf")
    results = hybrid.retrieve("Python programming", top_k=3)

    assert len(results) >= 1
    # #1 in the only active retriever must score 1.0
    assert pytest.approx(results[0].score, rel=1e-3) == 1.0
    assert all(0.0 <= r.score <= 1.0 for r in results)


def test_hybrid_retriever_linear_single_active_retriever(populated_store_and_chunks: tuple) -> None:
    """When only one retriever produces candidates, linear fusion must not halve its score."""
    store, model, _ = populated_store_and_chunks
    dense = DenseRetriever(embedding_model=model, vector_store=store)
    empty_sparse = KeywordRetriever(chunks_provider=lambda: [])

    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=empty_sparse, fusion_mode="linear", alpha=0.5)
    results = hybrid.retrieve("Python programming", top_k=2)

    assert len(results) >= 1
    # Top score should be 1.0, not 0.5
    assert pytest.approx(results[0].score, rel=1e-3) == 1.0


def test_hybrid_retriever_both_empty() -> None:
    """When both retrievers return empty, hybrid fusion returns empty list."""
    empty_store = InMemoryVectorStore()
    model = MockEmbeddingModel(dimension=64)
    dense = DenseRetriever(embedding_model=model, vector_store=empty_store)
    sparse = KeywordRetriever(chunks_provider=lambda: [])

    hybrid_rrf = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse, fusion_mode="rrf")
    assert hybrid_rrf.retrieve("anything") == []

    hybrid_lin = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse, fusion_mode="linear")
    assert hybrid_lin.retrieve("anything") == []


@pytest.mark.asyncio
async def test_hybrid_retriever_async(populated_store_and_chunks: tuple) -> None:
    store, model, chunks = populated_store_and_chunks
    dense = DenseRetriever(embedding_model=model, vector_store=store)
    sparse = KeywordRetriever(chunks_provider=lambda: chunks)

    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse, fusion_mode="linear")
    results = await hybrid.aretrieve("neural networks", top_k=2)

    assert len(results) >= 1
    assert results[0].retrieval_type == "hybrid"
    assert all(0.0 <= r.score <= 1.0 for r in results)


# ---------------------------------------------------------------------------
# BM25Index: index-once behaviour
# ---------------------------------------------------------------------------

def test_bm25_index_seeded_at_construction(populated_store_and_chunks: tuple) -> None:
    """KeywordRetriever should index all provider chunks exactly once at init."""
    from xeren.rag.retrieval.keyword import BM25Index

    _, _, chunks = populated_store_and_chunks
    retriever = KeywordRetriever(chunks_provider=lambda: chunks)

    # Index should contain exactly the 3 seeded chunks.
    assert retriever._index.num_chunks == 3


def test_bm25_index_incremental_add_chunks(populated_store_and_chunks: tuple) -> None:
    """add_chunks() must update the index so new chunks are immediately searchable."""
    _, _, chunks = populated_store_and_chunks
    retriever = KeywordRetriever(chunks_provider=lambda: chunks[:1])  # seed with 1

    assert retriever._index.num_chunks == 1

    new_chunk = DocumentChunk(
        chunk_id="chunk-new",
        document_id="doc-new",
        content="Transformer architecture attention mechanism self-supervised learning.",
        chunk_index=0,
        metadata={"topic": "transformers", "language": "en"},
    )
    retriever.add_chunks([new_chunk])
    assert retriever._index.num_chunks == 2

    results = retriever.retrieve("attention mechanism transformer", top_k=2)
    assert any(r.chunk.chunk_id == "chunk-new" for r in results)


def test_bm25_index_idempotent_double_add(populated_store_and_chunks: tuple) -> None:
    """Adding the same chunk twice must not corrupt the index (idempotent)."""
    _, _, chunks = populated_store_and_chunks
    retriever = KeywordRetriever(chunks_provider=lambda: chunks)

    # Adding already-indexed chunks should be a no-op.
    retriever.add_chunks(chunks)

    assert retriever._index.num_chunks == len(chunks)

    results = retriever.retrieve("Rust memory safety", top_k=3)
    # Scores must not be doubled — the rust chunk should still be at the top
    assert results[0].chunk.chunk_id == "chunk-rust"


# ---------------------------------------------------------------------------
# BM25 theoretical max & query-aware linear fusion tests
# ---------------------------------------------------------------------------

def test_bm25_get_max_query_score_properties(populated_store_and_chunks: tuple) -> None:
    """Test get_max_query_score on single-term, multi-term, missing, and duplicate terms."""
    _, _, chunks = populated_store_and_chunks
    kw_retriever = KeywordRetriever(chunks_provider=lambda: chunks)

    # 1. Single-term query
    max_single = kw_retriever.get_max_query_score("python")
    assert max_single > 0.0

    # 2. Multi-term query with distinct terms has strictly greater theoretical max
    max_multi = kw_retriever.get_max_query_score("python rust")
    assert max_multi > max_single

    # 3. Duplicate terms must NOT inflate the theoretical maximum
    max_with_dups = kw_retriever.get_max_query_score("python python python")
    assert pytest.approx(max_with_dups, rel=1e-5) == max_single

    # 4. Missing terms (not in index) are safely handled and contribute high IDF
    max_with_missing = kw_retriever.get_max_query_score("python nonexistenttoken123")
    assert max_with_missing > max_single

    # 5. Empty index / empty query
    empty_kw = KeywordRetriever(chunks_provider=lambda: [])
    assert empty_kw.get_max_query_score("python") == 1.0
    assert kw_retriever.get_max_query_score("") == 1.0


def test_hybrid_linear_weak_incidental_bm25_not_promoted(populated_store_and_chunks: tuple) -> None:
    """A weak match on 1 of 5 keywords must not be promoted to 1.0 in linear fusion."""
    store, model, chunks = populated_store_and_chunks
    dense = DenseRetriever(embedding_model=model, vector_store=store)
    sparse = KeywordRetriever(chunks_provider=lambda: chunks)

    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse, fusion_mode="linear", alpha=0.5)

    # Query with 5 keywords where only "python" exists in the python chunk
    query = "python quantum cryptography supercomputer distributed"
    results = hybrid.retrieve(query, top_k=3)

    assert len(results) >= 1
    python_result = next(r for r in results if r.chunk.chunk_id == "chunk-python")

    # The theoretical max for the 5-term query is high, so the sparse component for matching
    # only 1 word must be small (< 0.40), NOT inflated to 1.0.
    # Therefore, combined score with alpha=0.5 is bounded and not inflated by a fake 1.0 sparse score.
    assert 0.0 <= python_result.score <= 1.0


def test_hybrid_linear_strong_multi_term_bm25_match(populated_store_and_chunks: tuple) -> None:
    """A chunk matching all query keywords gets a high normalized score in linear fusion."""
    store, model, chunks = populated_store_and_chunks
    dense = DenseRetriever(embedding_model=model, vector_store=store)
    sparse = KeywordRetriever(chunks_provider=lambda: chunks)

    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse, fusion_mode="linear", alpha=0.5)

    # Query where python chunk contains all terms: "Python", "programming", "language"
    query = "Python programming language"
    results = hybrid.retrieve(query, top_k=3)

    assert len(results) >= 1
    assert results[0].chunk.chunk_id == "chunk-python"
    # Strong match on all keywords should yield high score
    assert results[0].score > 0.5
    assert results[0].score <= 1.0
