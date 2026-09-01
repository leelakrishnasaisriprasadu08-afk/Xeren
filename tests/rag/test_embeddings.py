"""Unit tests for embedding configurations, registry, and MockEmbeddingModel."""

import pytest
from pydantic import ValidationError

from xeren.models.errors import ProviderNotRegisteredError
from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.embeddings.config import EmbeddingConfig
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.embeddings.registry import EmbeddingRegistry


def test_embedding_config_validation() -> None:
    config = EmbeddingConfig(model_id="bge-small-en", provider="mock", dimension=384, batch_size=16)
    assert config.model_id == "bge-small-en"
    assert config.provider == "mock"
    assert config.dimension == 384
    assert config.batch_size == 16

    with pytest.raises(ValidationError):
        EmbeddingConfig(model_id="", provider="mock")

    with pytest.raises(ValidationError):
        EmbeddingConfig(model_id="m", provider="p", batch_size=-1)


def test_embedding_registry_create_mock() -> None:
    config = EmbeddingConfig(model_id="mock-1", provider="mock", dimension=128)
    model = EmbeddingRegistry.create(config)
    assert isinstance(model, MockEmbeddingModel)
    assert model.dimension == 128


def test_embedding_registry_unknown_raises() -> None:
    config = EmbeddingConfig(model_id="embed-x", provider="nonexistent_provider")
    with pytest.raises(ProviderNotRegisteredError):
        EmbeddingRegistry.create(config)


def test_mock_embedding_generation() -> None:
    model = MockEmbeddingModel(dimension=64)

    # Query embedding
    q_vec = model.embed_query("search query")
    assert len(q_vec) == 64
    assert isinstance(q_vec[0], float)

    # Determinism check
    q_vec_2 = model.embed_query("search query")
    assert q_vec == q_vec_2

    # Document batch
    d_vecs = model.embed_documents(["doc 1", "doc 2"])
    assert len(d_vecs) == 2
    assert len(d_vecs[0]) == 64
    assert len(d_vecs[1]) == 64
    assert d_vecs[0] != d_vecs[1]


@pytest.mark.asyncio
async def test_mock_async_embedding() -> None:
    model = MockEmbeddingModel(dimension=32)
    q_vec = await model.aembed_query("async search")
    assert len(q_vec) == 32

    d_vecs = await model.aembed_documents(["doc a", "doc b"])
    assert len(d_vecs) == 2


def test_mock_embed_chunks() -> None:
    model = MockEmbeddingModel(dimension=48)
    chunk = DocumentChunk(
        document_id="doc-1",
        content="This is chunk text",
        chunk_index=0,
        total_chunks=1,
    )

    embedded_chunks = model.embed_chunks([chunk])
    assert len(embedded_chunks) == 1
    assert isinstance(embedded_chunks[0], EmbeddedChunk)
    assert embedded_chunks[0].chunk == chunk
    assert len(embedded_chunks[0].embedding) == 48
    assert embedded_chunks[0].dimension == 48
    assert embedded_chunks[0].embedding_model == "mock-embed"
