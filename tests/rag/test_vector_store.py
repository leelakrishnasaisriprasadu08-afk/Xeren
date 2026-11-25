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


def test_vector_store_empty_store_behavior() -> None:
    store = InMemoryVectorStore()
    assert store.count() == 0
    assert store.similarity_search(query_vector=[1.0, 0.0, 0.0], top_k=4) == []
    assert store.delete(["nonexistent_id"]) == 0
    assert store.get_all_chunks() == []


def test_vector_store_delete_and_clear(sample_chunks: list[EmbeddedChunk]) -> None:
    store = InMemoryVectorStore()
    store.add_chunks(sample_chunks)

    deleted_count = store.delete(["c1"])
    assert deleted_count == 1
    assert store.count() == 2

    store.clear()
    assert store.count() == 0
    assert store.similarity_search(query_vector=[1.0, 0.0, 0.0]) == []


def test_embedding_vector_store_retrieval_and_reranking_pipeline() -> None:
    """End-to-end data path: Local Embedding Adapter -> Vector Store -> Dense Retrieval -> Reranking."""
    import json
    import httpx
    from xeren.rag.embeddings.config import EmbeddingConfig
    from xeren.rag.embeddings.providers.local_openweight import LocalOpenWeightEmbeddingAdapter
    from xeren.rag.rerankers.local import LocalReranker
    from xeren.rag.retrieval.dense import DenseRetriever

    # 1. Setup mock transport for local embedding adapter
    def mock_embedding_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        inputs = body["input"]
        # Return deterministic mock embeddings based on text content
        data = []
        for i, text in enumerate(inputs):
            if "vector" in text.lower() or "database" in text.lower():
                vec = [0.9, 0.1, 0.0]
            elif "compiler" in text.lower() or "rust" in text.lower():
                vec = [0.0, 0.9, 0.1]
            else:
                vec = [0.1, 0.1, 0.8]
            data.append({"object": "embedding", "index": i, "embedding": vec})
        return httpx.Response(200, json={"object": "list", "model": "local-embed", "data": data})

    client = httpx.Client(transport=httpx.MockTransport(mock_embedding_handler))
    config = EmbeddingConfig(model_id="local-embed", provider="local_openweight", api_base="http://localhost:11434/v1")
    embedder = LocalOpenWeightEmbeddingAdapter(config=config, client=client)

    # 2. Embed chunks and store in vector store
    store = InMemoryVectorStore()
    chunks = [
        DocumentChunk(
            chunk_id="chk-vec",
            document_id="doc-rag",
            content="Vector databases index embeddings for high-dimensional nearest neighbor search.",
            chunk_index=0,
            metadata={"source": "rag_docs.md", "topic": "vector_search"},
        ),
        DocumentChunk(
            chunk_id="chk-comp",
            document_id="doc-rust",
            content="Rust compilers perform borrow checking and lifetime analysis.",
            chunk_index=0,
            metadata={"source": "rust_docs.md", "topic": "compilers"},
        ),
    ]

    embedded = embedder.embed_chunks(chunks)
    inserted_ids = store.add_chunks(embedded)
    assert inserted_ids == ["chk-vec", "chk-comp"]
    assert store.count() == 2

    # 3. Dense retrieval
    retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
    query = "high-dimensional vector database search"
    retrieved = retriever.retrieve(query, top_k=2)

    assert len(retrieved) == 2
    assert retrieved[0].chunk.chunk_id == "chk-vec"
    assert retrieved[0].chunk.metadata["source"] == "rag_docs.md"
    assert retrieved[0].retrieval_type == "dense"

    # 4. Local Reranking
    reranker = LocalReranker()
    reranked = reranker.rerank(query, retrieved, top_n=1)

    assert len(reranked) == 1
    assert reranked[0].chunk.chunk_id == "chk-vec"
    assert reranked[0].retrieval_type == "reranked"
    assert reranked[0].score > 0.5
    assert reranked[0].chunk.metadata["topic"] == "vector_search"

