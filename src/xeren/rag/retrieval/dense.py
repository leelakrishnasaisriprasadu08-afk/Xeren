"""Dense semantic retriever using embedding models and vector stores."""

from typing import List, Optional

from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.base import VectorStore


class DenseRetriever(BaseRetriever):
    """Semantic retriever using vector embeddings and vector store similarity search."""

    def __init__(
        self,
        embedding_model: BaseEmbeddingModel,
        vector_store: VectorStore,
    ) -> None:
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        if not query or not query.strip():
            return []

        query_vector = self.embedding_model.embed_query(query)
        results = self.vector_store.similarity_search(
            query_vector=query_vector,
            top_k=top_k,
            filter=filter,
        )
        for r in results:
            r.retrieval_type = "dense"
        return results

    async def aretrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        if not query or not query.strip():
            return []

        query_vector = await self.embedding_model.aembed_query(query)
        results = await self.vector_store.asimilarity_search(
            query_vector=query_vector,
            top_k=top_k,
            filter=filter,
        )
        for r in results:
            r.retrieval_type = "dense"
        return results
