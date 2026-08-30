"""Hybrid retriever combining dense semantic and sparse keyword retrieval."""

import asyncio
from typing import Dict, List, Literal, Optional

from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult


class HybridRetriever(BaseRetriever):
    """Combines semantic (dense) and lexical (sparse) retrieval strategies."""

    def __init__(
        self,
        dense_retriever: BaseRetriever,
        sparse_retriever: BaseRetriever,
        fusion_mode: Literal["rrf", "linear"] = "rrf",
        rrf_k: int = 60,
        alpha: float = 0.5,
    ) -> None:
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.fusion_mode = fusion_mode
        self.rrf_k = rrf_k
        self.alpha = alpha  # Weight for dense in linear fusion

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[SearchResult],
        sparse_results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, DocumentChunk] = {}

        for rank, res in enumerate(dense_results, start=1):
            cid = res.chunk.chunk_id
            chunk_map[cid] = res.chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        for rank, res in enumerate(sparse_results, start=1):
            cid = res.chunk.chunk_id
            chunk_map[cid] = res.chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        return [
            SearchResult(
                chunk=chunk_map[cid],
                score=rrf_scores[cid],
                retrieval_type="hybrid",
            )
            for cid in sorted_cids[:top_k]
        ]

    def _linear_score_fusion(
        self,
        dense_results: List[SearchResult],
        sparse_results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        combined_scores: Dict[str, float] = {}
        chunk_map: Dict[str, DocumentChunk] = {}

        # Normalize dense scores
        max_dense = max((r.score for r in dense_results), default=1.0) or 1.0
        for r in dense_results:
            cid = r.chunk.chunk_id
            chunk_map[cid] = r.chunk
            norm_score = max(0.0, r.score) / max_dense
            combined_scores[cid] = combined_scores.get(cid, 0.0) + self.alpha * norm_score

        # Normalize sparse scores
        max_sparse = max((r.score for r in sparse_results), default=1.0) or 1.0
        for r in sparse_results:
            cid = r.chunk.chunk_id
            chunk_map[cid] = r.chunk
            norm_score = max(0.0, r.score) / max_sparse
            combined_scores[cid] = combined_scores.get(cid, 0.0) + (1.0 - self.alpha) * norm_score

        sorted_cids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
        return [
            SearchResult(
                chunk=chunk_map[cid],
                score=combined_scores[cid],
                retrieval_type="hybrid",
            )
            for cid in sorted_cids[:top_k]
        ]

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        dense_results = self.dense_retriever.retrieve(query, top_k=top_k * 2, filter=filter)
        sparse_results = self.sparse_retriever.retrieve(query, top_k=top_k * 2, filter=filter)

        if self.fusion_mode == "rrf":
            return self._reciprocal_rank_fusion(dense_results, sparse_results, top_k)
        return self._linear_score_fusion(dense_results, sparse_results, top_k)

    async def aretrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        dense_task = self.dense_retriever.aretrieve(query, top_k=top_k * 2, filter=filter)
        sparse_task = self.sparse_retriever.aretrieve(query, top_k=top_k * 2, filter=filter)
        dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)

        if self.fusion_mode == "rrf":
            return self._reciprocal_rank_fusion(dense_results, sparse_results, top_k)
        return self._linear_score_fusion(dense_results, sparse_results, top_k)
