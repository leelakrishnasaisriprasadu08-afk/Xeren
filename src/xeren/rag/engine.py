"""Grounded RAG query engine orchestrating retrieve -> rerank -> select -> construct context."""

import asyncio
import logging
from typing import Optional

from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import GroundedContext
from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.filter import MetadataFilter

logger = logging.getLogger("xeren.rag.engine")


class RAGQueryEngine:
    """End-to-end RAG query orchestrator for grounded context construction."""

    def __init__(
        self,
        retriever: BaseRetriever,
        reranker: Optional[BaseReranker] = None,
        context_builder: Optional[ContextBuilder] = None,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder or ContextBuilder()

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        top_n: Optional[int] = 5,
        filter: Optional[MetadataFilter] = None,
    ) -> GroundedContext:
        """Execute complete retrieval, reranking, and grounded context construction pipeline."""
        logger.debug("Executing RAG query: %s", query_text)

        # 1. Retrieve candidate chunks
        candidates = self.retriever.retrieve(query_text, top_k=top_k, filter=filter)
        if not candidates:
            return self.context_builder.build([])

        # 2. Rerank candidates if reranker is configured
        if self.reranker:
            reranked = self.reranker.rerank(query_text, candidates, top_n=top_n)
        else:
            reranked = candidates[:top_n] if top_n is not None else candidates

        # 3. Select within budget and construct grounded context with citations
        grounded_context = self.context_builder.build(reranked)

        logger.info(
            "RAG query context constructed",
            extra={
                "query": query_text,
                "candidates_count": len(candidates),
                "selected_chunks": len(grounded_context.selected_chunks),
                "tokens": grounded_context.estimated_tokens,
            },
        )
        return grounded_context

    async def aquery(
        self,
        query_text: str,
        top_k: int = 10,
        top_n: Optional[int] = 5,
        filter: Optional[MetadataFilter] = None,
    ) -> GroundedContext:
        """Asynchronously execute retrieval, reranking, and context construction."""
        candidates = await self.retriever.aretrieve(query_text, top_k=top_k, filter=filter)
        if not candidates:
            return self.context_builder.build([])

        if self.reranker:
            reranked = await self.reranker.arerank(query_text, candidates, top_n=top_n)
        else:
            reranked = candidates[:top_n] if top_n is not None else candidates

        return self.context_builder.build(reranked)
