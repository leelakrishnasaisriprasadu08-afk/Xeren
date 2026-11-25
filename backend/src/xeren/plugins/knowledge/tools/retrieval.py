"""Retrieval tool wrapping existing Xeren dense, keyword, and hybrid retrievers."""

import logging
from typing import List, Optional

from xeren.plugins.knowledge.schemas import RetrievalMode
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.hybrid import HybridRetriever
from xeren.rag.retrieval.keyword import KeywordRetriever
from xeren.rag.retrieval.types import SearchResult

logger = logging.getLogger("xeren.plugins.knowledge.tools.retrieval")


class KnowledgeRetrievalTool:
    """Delegates retrieval requests directly to existing Xeren retriever components."""

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        keyword_retriever: KeywordRetriever,
        hybrid_retriever: HybridRetriever,
    ) -> None:
        self.dense_retriever = dense_retriever
        self.keyword_retriever = keyword_retriever
        self.hybrid_retriever = hybrid_retriever

    def get_retriever(self, mode: RetrievalMode) -> BaseRetriever:
        """Select the target retriever based on requested mode."""
        if mode == RetrievalMode.DENSE:
            return self.dense_retriever
        elif mode == RetrievalMode.KEYWORD:
            return self.keyword_retriever
        return self.hybrid_retriever

    def retrieve(
        self,
        query: str,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        top_k: int = 5,
        filter: Optional[MetadataFilter] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Retrieve candidate search results using the selected existing retriever."""
        retriever = self.get_retriever(mode)
        candidates = retriever.retrieve(
            query=query,
            top_k=top_k,
            filter=filter,
        )

        if min_score > 0.0:
            candidates = [c for c in candidates if c.score >= min_score]

        return candidates


__all__ = ["KnowledgeRetrievalTool"]
