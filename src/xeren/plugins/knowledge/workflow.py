"""Autonomous Knowledge/RAG workflow orchestrating ingestion, retrieval, reranking, and context construction."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from xeren.plugins.knowledge.registry import KnowledgeToolRegistry
from xeren.plugins.knowledge.schemas import (
    KnowledgeInput,
    KnowledgeOperation,
    KnowledgeResult,
    RetrievalMode,
)
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import Citation, GroundedContext
from xeren.rag.document import Document, DocumentChunk
from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.pipeline import IngestionPipeline
from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.retrieval.hybrid import HybridRetriever
from xeren.rag.retrieval.keyword import KeywordRetriever
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.base import VectorStore

logger = logging.getLogger("xeren.plugins.knowledge.workflow")


class KnowledgeWorkflow:
    """Orchestrates existing Xeren RAG components into a unified knowledge workflow."""

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
        registry: Optional[KnowledgeToolRegistry] = None,
    ) -> None:
        self.registry = registry or KnowledgeToolRegistry(
            vector_store=vector_store,
            embedding_model=embedding_model,
            keyword_retriever=keyword_retriever,
            dense_retriever=dense_retriever,
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
            context_builder=context_builder,
            ingestion_pipeline=ingestion_pipeline,
        )

        self.vector_store = self.registry.vector_store
        self.embedding_model = self.registry.embedding_model
        self.keyword_retriever = self.registry.keyword_retriever
        self.dense_retriever = self.registry.dense_retriever
        self.hybrid_retriever = self.registry.hybrid_retriever
        self.reranker = self.registry.reranker
        self.context_builder = self.registry.context_builder
        self.ingestion_pipeline = self.registry.ingestion_pipeline

        self.retrieval_tool = self.registry.retrieval_tool
        self.ingestion_tool = self.registry.ingestion_tool
        self.context_tool = self.registry.context_tool
        self.provenance_tool = self.registry.provenance_tool

    def _select_retriever(self, mode: RetrievalMode) -> BaseRetriever:
        """Select the appropriate retriever strategy based on requested mode."""
        return self.retrieval_tool.get_retriever(mode)

    # -------------------------------------------------------------------------
    # Ingestion Workflow
    # -------------------------------------------------------------------------
    def execute_ingest(self, input_data: KnowledgeInput) -> KnowledgeResult:
        """Ingest documents or raw texts using the existing IngestionPipeline."""
        start_time = time.perf_counter()
        inserted_ids = self.ingestion_tool.ingest_batch(
            texts=input_data.texts,
            documents=input_data.documents,
            source=input_data.source,
            metadata=input_data.metadata,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "Knowledge ingestion completed: %d chunk(s) indexed in %.2fms",
            len(inserted_ids),
            latency_ms,
        )

        return KnowledgeResult(
            operation=KnowledgeOperation.INGEST,
            inserted_chunk_ids=inserted_ids,
            execution_stats={
                "latency_ms": latency_ms,
                "inserted_count": len(inserted_ids),
                "source": input_data.source,
            },
            success=True,
        )

    async def aexecute_ingest(self, input_data: KnowledgeInput) -> KnowledgeResult:
        """Asynchronously execute knowledge ingestion."""
        return await asyncio.to_thread(self.execute_ingest, input_data)

    # -------------------------------------------------------------------------
    # Query & Retrieval Workflow
    # -------------------------------------------------------------------------
    def execute_query(self, input_data: KnowledgeInput) -> KnowledgeResult:
        """Execute knowledge retrieval, reranking, context assembly, and provenance mapping."""
        start_time = time.perf_counter()
        query = str(input_data.query).strip()

        # 1. Retrieve candidate search results via retrieval tool
        candidates = self.retrieval_tool.retrieve(
            query=query,
            mode=input_data.retrieval_mode,
            top_k=input_data.top_k,
            filter=input_data.filter,
            min_score=input_data.min_score,
        )

        # 2. Rerank candidates using existing reranker
        if self.reranker is not None and candidates:
            reranked = self.reranker.rerank(query, candidates, top_n=input_data.top_n)
        else:
            reranked = candidates[:input_data.top_n] if input_data.top_n is not None else candidates

        # 3. Construct grounded context via context tool
        grounded_context: Optional[GroundedContext] = None
        if input_data.include_context:
            grounded_context = self.context_tool.build_context(reranked)

        # 4. Attach provenance citations via provenance tool
        citations: List[Citation] = []
        if input_data.include_provenance:
            citations = self.provenance_tool.get_provenance(reranked, context=grounded_context)

        # 5. Extract retrieved chunks and scores
        retrieved_chunks = [r.chunk for r in reranked]
        scores_map = {r.chunk.chunk_id: round(r.score, 4) for r in reranked}

        # 6. Identify knowledge gaps
        knowledge_gaps: List[str] = []
        if not reranked:
            knowledge_gaps.append(f"No relevant knowledge chunks found for '{query}'.")
        elif reranked[0].score < 0.3:
            knowledge_gaps.append(
                f"Low retrieval confidence (top score: {reranked[0].score:.2f}) for '{query}'."
            )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "Knowledge query '%s' retrieved %d candidates, selected %d chunks in %.2fms (mode: %s)",
            query,
            len(candidates),
            len(reranked),
            latency_ms,
            input_data.retrieval_mode.value,
        )

        return KnowledgeResult(
            operation=KnowledgeOperation.QUERY,
            query=query,
            retrieved_chunks=retrieved_chunks,
            ranked_results=reranked,
            context=grounded_context,
            provenance=citations,
            retrieval_scores=scores_map,
            knowledge_gaps=knowledge_gaps,
            execution_stats={
                "latency_ms": latency_ms,
                "candidates_count": len(candidates),
                "selected_count": len(reranked),
                "retrieval_mode": input_data.retrieval_mode.value,
            },
            success=True,
        )

    async def aexecute_query(self, input_data: KnowledgeInput) -> KnowledgeResult:
        """Asynchronously execute knowledge retrieval and context assembly."""
        return await asyncio.to_thread(self.execute_query, input_data)

    # -------------------------------------------------------------------------
    # Main Workflow Dispatcher
    # -------------------------------------------------------------------------
    def run(self, input_data: KnowledgeInput) -> KnowledgeResult:
        """Execute the workflow based on the requested operation."""
        if input_data.operation == KnowledgeOperation.INGEST:
            return self.execute_ingest(input_data)
        return self.execute_query(input_data)

    async def arun(self, input_data: KnowledgeInput) -> KnowledgeResult:
        """Asynchronously execute the workflow based on the requested operation."""
        if input_data.operation == KnowledgeOperation.INGEST:
            return await self.aexecute_ingest(input_data)
        return await self.aexecute_query(input_data)


__all__ = ["KnowledgeWorkflow"]
