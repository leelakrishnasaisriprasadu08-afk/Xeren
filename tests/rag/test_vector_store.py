"""Unit tests for InMemoryVectorStore."""

import pytest

from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.retrieval.filter import FilterCondition, FilterOperator, MetadataFilter
from xeren.rag.stores.memory_store import InMemoryVectorStore


@pytest.fixture
def sample_chunks() -> list[EmbeddedChunk]:
    c1 = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        content="Machine learning neural networks",
        chunk_index=0,
        metadata={"category": "ai", "difficulty": 1},
    )
    c2 = DocumentChunk(
        chunk_id="c2",
        document_id="d1",
        content="Deep learning backpropagation",
        chunk_index=1,
        metadata={"category": "ai", "difficulty": 3},
    )
    c3 = DocumentChunk(
        chunk_id="c3",
        document_id="d2",
        content="Web development HTML CSS",
        chunk_index=0,
        metadata={"category": "web", "difficulty": 1},
    )

    return [
        EmbeddedChunk(chunk=c1, embedding=[1.0, 0.0, 0.0], embedding_model="m1"),
        EmbeddedChunk(chunk=c2, embedding=[0.8, 0.6, 0.0], embedding_model="m1"),
        EmbeddedChunk(chunk=c3, embedding=[0.0, 0.0, 1.0], embedding_model="m1"),
    ]


def test_vector_store_add_and_count(sample_chunks: list[EmbeddedChunk]) -> None:
    store = InMemoryVectorStore()
    inserted_ids = store.add_chunks(sample_chunks)

    assert len(inserted_ids) == 3
    assert store.count() == 3


def test_vector_store_similarity_search(sample_chunks: list[EmbeddedChunk]) -> None:
    store = InMemoryVectorStore()
    store.add_chunks(sample_chunks)

    # Query vector close to c1
    results = store.similarity_search(query_vector=[1.0, 0.0, 0.0], top_k=2)

    assert len(results) == 2
    assert results[0].chunk.chunk_id == "c1"
    assert results[0].score == pytest.approx(1.0, abs=1e-4)
    assert results[1].chunk.chunk_id == "c2"
    assert results[1].score == pytest.approx(0.8, abs=1e-4)


def test_vector_store_filtered_search(sample_chunks: list[EmbeddedChunk]) -> None:
    store = InMemoryVectorStore()
    store.add_chunks(sample_chunks)

    # Search with filter category == 'web'
    flt = MetadataFilter.eq("category", "web")
    results = store.similarity_search(query_vector=[1.0, 0.0, 0.0], top_k=5, filter=flt)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "c3"


def test_vector_store_delete_and_clear(sample_chunks: list[EmbeddedChunk]) -> None:
    store = InMemoryVectorStore()
    store.add_chunks(sample_chunks)

    deleted_count = store.delete(["c1"])
    assert deleted_count == 1
    assert store.count() == 2

    store.clear()
    assert store.count() == 0
