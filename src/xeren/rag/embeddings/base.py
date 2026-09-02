"""Abstract base interfaces for RAG embedding models and embedded chunk containers."""

import asyncio
from typing import Any, List
from pydantic import BaseModel, Field

from xeren.models.base import BaseEmbeddingModel as CoreBaseEmbeddingModel
from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.config import EmbeddingConfig


class EmbeddedChunk(BaseModel):
    """A DocumentChunk combined with its dense vector embedding and model provenance."""

    chunk: DocumentChunk = Field(..., description="The source DocumentChunk")
    embedding: List[float] = Field(..., description="Dense vector embedding values")
    embedding_model: str = Field(..., description="Name/ID of the model that generated this embedding")
    dimension: int = Field(default=0, ge=0, description="Dimensionality of the vector")

    def model_post_init(self, __context: Any) -> None:
        if not self.dimension:
            self.dimension = len(self.embedding)


class BaseEmbeddingModel(CoreBaseEmbeddingModel):
    """Abstract base class for all RAG embedding models in Xeren."""

    def __init__(self, config: EmbeddingConfig) -> None:
        super().__init__(config=config)
        self.config: EmbeddingConfig = config

    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[EmbeddedChunk]:
        """Generate dense vector embeddings for a list of DocumentChunks."""
        if not chunks:
            return []
        texts = [chunk.content for chunk in chunks]
        vectors = self.embed_documents(texts)
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self.config.model_id,
                dimension=len(vector),
            )
            for chunk, vector in zip(chunks, vectors)
        ]

    async def aembed_chunks(self, chunks: List[DocumentChunk]) -> List[EmbeddedChunk]:
        """Asynchronously generate dense vector embeddings for a list of DocumentChunks."""
        if not chunks:
            return []
        texts = [chunk.content for chunk in chunks]
        vectors = await self.aembed_documents(texts)
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self.config.model_id,
                dimension=len(vector),
            )
            for chunk, vector in zip(chunks, vectors)
        ]


__all__ = ["BaseEmbeddingModel", "EmbeddedChunk"]
