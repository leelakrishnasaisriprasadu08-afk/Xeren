"""Tool registry aggregating knowledge and RAG capabilities for workflow execution."""

from typing import Optional

from xeren.plugins.knowledge.tools.context import KnowledgeContextTool
from xeren.plugins.knowledge.tools.ingestion import KnowledgeIngestionTool
from xeren.plugins.knowledge.tools.provenance import KnowledgeProvenanceTool
from xeren.plugins.knowledge.tools.retrieval import KnowledgeRetrievalTool
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.pipeline import IngestionPipeline
from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.rerankers.threshold import ScoreThresholdReranker
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.retrieval.hybrid import HybridRetriever
from xeren.rag.retrieval.keyword import KeywordRetriever
from xeren.rag.stores.base import VectorStore
from xeren.rag.stores.memory_store import InMemoryVectorStore


class KnowledgeToolRegistry:
    """Registry maintaining initialized RAG components and tools for the KnowledgePlugin."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        keyword_retriever: Optional[KeywordRetriever] = None,
        dense_retriever: Optional[DenseRetriever] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[BaseReranker] = None,
        context_builder: Optional[ContextBuilder] = None,
        ingestion_pipeline: Optional[IngestionPipeline] = None,
    ) -> None:
        self.vector_store = vector_store or InMemoryVectorStore()
        self.embedding_model = embedding_model or MockEmbeddingModel(dimension=64)
        self.keyword_retriever = keyword_retriever or KeywordRetriever()

        self.dense_retriever = dense_retriever or DenseRetriever(
            embedding_model=self.embedding_model,
            vector_store=self.vector_store,
        )

        self.hybrid_retriever = hybrid_retriever or HybridRetriever(
            dense_retriever=self.dense_retriever,
            sparse_retriever=self.keyword_retriever,
        )

        self.reranker = reranker or ScoreThresholdReranker(min_score=0.0)
        self.context_builder = context_builder or ContextBuilder()

        # Synchronized ingestion pipeline
        self.ingestion_pipeline = ingestion_pipeline or IngestionPipeline(
            embedding_model=self.embedding_model,
            vector_store=self.vector_store,
            keyword_retriever=self.keyword_retriever,
        )

        # Internal tool wrappers
        self.retrieval_tool = KnowledgeRetrievalTool(
            dense_retriever=self.dense_retriever,
            keyword_retriever=self.keyword_retriever,
            hybrid_retriever=self.hybrid_retriever,
        )
        self.ingestion_tool = KnowledgeIngestionTool(pipeline=self.ingestion_pipeline)
        self.context_tool = KnowledgeContextTool(builder=self.context_builder)
        self.provenance_tool = KnowledgeProvenanceTool()


__all__ = ["KnowledgeToolRegistry"]
