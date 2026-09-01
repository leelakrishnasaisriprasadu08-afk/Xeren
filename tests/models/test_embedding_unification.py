"""Unit tests verifying BaseEmbeddingModel unification across models and rag packages."""

from xeren.models.base import BaseEmbeddingModel as ModelsBaseEmbedding
from xeren.rag.embeddings.base import BaseEmbeddingModel as RagBaseEmbedding
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel


def test_embedding_class_hierarchy() -> None:
    # Ensure RagBaseEmbedding subclasses ModelsBaseEmbedding cleanly
    assert issubclass(RagBaseEmbedding, ModelsBaseEmbedding)
    model = MockEmbeddingModel(dimension=32)
    assert isinstance(model, ModelsBaseEmbedding)
    assert isinstance(model, RagBaseEmbedding)


def test_compatibility_methods() -> None:
    model = MockEmbeddingModel(dimension=32)

    # Test embed_text alias
    vec1 = model.embed_text("sample text")
    vec2 = model.embed_query("sample text")
    assert vec1 == vec2
    assert len(vec1) == 32

    # Test embed_batch alias
    batch1 = model.embed_batch(["text a", "text b"])
    batch2 = model.embed_documents(["text a", "text b"])
    assert batch1 == batch2
    assert len(batch1) == 2
