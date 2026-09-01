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
        if not dense_results and not sparse_results:
            return []

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

        # Normalize scores to [0.0, 1.0] using theoretical maximum of active retrievers
        num_active = (1 if dense_results else 0) + (1 if sparse_results else 0)
        max_possible_score = num_active * (1.0 / (self.rrf_k + 1)) if num_active > 0 else 1.0

        sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        return [
            SearchResult(
                chunk=chunk_map[cid],
                score=rrf_scores[cid] / max_possible_score,
                retrieval_type="hybrid",
            )
            for cid in sorted_cids[:top_k]
        ]

    def _linear_score_fusion(
        self,
        dense_results: List[SearchResult],
        sparse_results: List[SearchResult],
        top_k: int,
        query: Optional[str] = None,
    ) -> List[SearchResult]:
        if not dense_results and not sparse_results:
            return []

        combined_scores: Dict[str, float] = {}
        chunk_map: Dict[str, DocumentChunk] = {}

        # Compute active weights so a single retriever is not artificially penalized
        has_dense = bool(dense_results)
        has_sparse = bool(sparse_results)

        if has_dense and has_sparse:
            dense_weight = self.alpha
            sparse_weight = 1.0 - self.alpha
        elif has_dense:
            dense_weight = 1.0
            sparse_weight = 0.0
        else:
            dense_weight = 0.0
            sparse_weight = 1.0

        if has_dense:
            max_dense = max((r.score for r in dense_results), default=1.0)
            max_dense = max_dense if max_dense > 0.0 else 1.0
            for r in dense_results:
                cid = r.chunk.chunk_id
                chunk_map[cid] = r.chunk
                norm_score = max(0.0, r.score) / max_dense
                combined_scores[cid] = combined_scores.get(cid, 0.0) + dense_weight * norm_score

        if has_sparse:
            if query and hasattr(self.sparse_retriever, "get_max_query_score"):
                max_sparse = self.sparse_retriever.get_max_query_score(query)
            else:
                max_sparse = max((r.score for r in sparse_results), default=1.0)
            max_sparse = max_sparse if max_sparse > 0.0 else 1.0
            for r in sparse_results:
                cid = r.chunk.chunk_id
                chunk_map[cid] = r.chunk
                norm_score = min(1.0, max(0.0, r.score) / max_sparse)
                combined_scores[cid] = combined_scores.get(cid, 0.0) + sparse_weight * norm_score

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
        return self._linear_score_fusion(dense_results, sparse_results, top_k, query=query)

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
        return self._linear_score_fusion(dense_results, sparse_results, top_k, query=query)
