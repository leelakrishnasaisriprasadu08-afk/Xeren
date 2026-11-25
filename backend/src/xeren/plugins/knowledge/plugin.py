"""Knowledge/RAG Plugin implementation conforming to the Xeren BasePlugin contract."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.knowledge.manifest import KNOWLEDGE_PLUGIN_MANIFEST
from xeren.plugins.knowledge.schemas import (
    KnowledgeInput,
    KnowledgeOperation,
    KnowledgeResult,
    RetrievalMode,
)
from xeren.plugins.knowledge.workflow import KnowledgeWorkflow
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.document import Document
from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.pipeline import IngestionPipeline
from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.hybrid import HybridRetriever
from xeren.rag.retrieval.keyword import KeywordRetriever
from xeren.rag.stores.base import VectorStore

logger = logging.getLogger("xeren.plugins.knowledge.plugin")


class KnowledgePlugin(BasePlugin):
    """Modular Knowledge and Grounded RAG Plugin for Xeren Core."""

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
        workflow: Optional[KnowledgeWorkflow] = None,
        registry: Optional[Any] = None,
    ) -> None:
        self.workflow = workflow or KnowledgeWorkflow(
            vector_store=vector_store,
            embedding_model=embedding_model,
            keyword_retriever=keyword_retriever,
            dense_retriever=dense_retriever,
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
            context_builder=context_builder,
            ingestion_pipeline=ingestion_pipeline,
            registry=registry,
        )
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return KNOWLEDGE_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return KnowledgeInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return KnowledgeResult

    # -------------------------------------------------------------------------
    # Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute a knowledge query or ingestion operation."""
        start_time = time.perf_counter()
        try:
            validated_input: KnowledgeInput = self.validate_input(input_data)  # type: ignore
            result: KnowledgeResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=result,
                latency_ms=latency_ms,
                metadata={
                    "operation": result.operation.value,
                    "retrieved_count": len(result.retrieved_chunks),
                    "inserted_count": len(result.inserted_chunk_ids),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("KnowledgePlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"KnowledgePlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute a knowledge query or ingestion operation."""
        start_time = time.perf_counter()
        try:
            validated_input: KnowledgeInput = self.validate_input(input_data)  # type: ignore
            result: KnowledgeResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=result,
                latency_ms=latency_ms,
                metadata={
                    "operation": result.operation.value,
                    "retrieved_count": len(result.retrieved_chunks),
                    "inserted_count": len(result.inserted_chunk_ids),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("KnowledgePlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"KnowledgePlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Convenience Typed Interfaces
    # -------------------------------------------------------------------------
    def query(
        self,
        query: str,
        top_k: int = 5,
        top_n: Optional[int] = 5,
        retrieval_mode: Union[RetrievalMode, str] = RetrievalMode.HYBRID,
        min_score: float = 0.0,
        filter: Optional[MetadataFilter] = None,
        include_context: bool = True,
        include_provenance: bool = True,
        **kwargs: Any,
    ) -> KnowledgeResult:
        """Convenience method to query the knowledge base directly."""
        mode = RetrievalMode(retrieval_mode) if isinstance(retrieval_mode, str) else retrieval_mode
        inp = KnowledgeInput(
            query=query,
            operation=KnowledgeOperation.QUERY,
            top_k=top_k,
            top_n=top_n,
            retrieval_mode=mode,
            min_score=min_score,
            filter=filter,
            include_context=include_context,
            include_provenance=include_provenance,
            metadata=kwargs,
        )
        return self.workflow.execute_query(inp)

    def ingest(
        self,
        texts: Optional[List[str]] = None,
        documents: Optional[List[Document]] = None,
        source: str = "knowledge_ingest",
        **kwargs: Any,
    ) -> KnowledgeResult:
        """Convenience method to ingest knowledge directly."""
        inp = KnowledgeInput(
            operation=KnowledgeOperation.INGEST,
            texts=texts,
            documents=documents,
            source=source,
            metadata=kwargs,
        )
        return self.workflow.execute_ingest(inp)

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Check status of embedding model, vector store, and keyword index."""
        start_time = time.perf_counter()

        embed_ok = True
        try:
            embed_ok = self.workflow.embedding_model.ping()
        except Exception:
            embed_ok = False

        vector_count = 0
        try:
            vector_count = self.workflow.vector_store.count()
        except Exception:
            pass

        details = {
            "embedding_model": type(self.workflow.embedding_model).__name__,
            "embedding_healthy": embed_ok,
            "vector_store": type(self.workflow.vector_store).__name__,
            "indexed_vector_chunks": vector_count,
            "retriever_type": type(self.workflow.hybrid_retriever).__name__,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status = PluginHealthStatus.HEALTHY if embed_ok else PluginHealthStatus.DEGRADED

        return HealthCheckResult(
            status=status,
            details=details,
            latency_ms=latency_ms,
            error=None if embed_ok else "Embedding model ping check failed.",
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational health."""
        return await asyncio.to_thread(self.health_check)

    def health(self) -> HealthCheckResult:
        """Alias for health_check conforming to plugin contract."""
        return self.health_check()

    def initialize(self) -> None:
        """Initialize plugin state and verify resources."""
        self._initialized = True

    def shutdown(self) -> None:
        """Release any open resources."""
        self._initialized = False


__all__ = ["KnowledgePlugin"]

