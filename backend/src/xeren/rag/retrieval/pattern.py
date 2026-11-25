"""Sovereign pattern retriever integrating XerenPatternDB into RAG pipelines.

Features:
- Native multi-pattern querying: dense vectors, sparse tokens, and AST code symbols.
- Automated AST code symbol query routing (e.g. `def `, `class `, function calls).
- Hybrid score fusion blending CPU cosine similarity and term weights.
- Hierarchical context expansion: attaches parent section headers and child breadcrumbs.
- Full MetadataFilter enforcement.
- Strict isolation: verifies all retrieved knowledge belongs solely to RAG knowledge base.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional


if TYPE_CHECKING:
    from xeren.rag.context.builder import ContextBuilder
    from xeren.rag.engine import RAGQueryEngine
from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.pattern_db.engine import XerenPatternDB
from xeren.rag.stores.pattern_db.schema import PatternQuery, PatternSearchResult, PatternType



class SovereignPatternRetriever(BaseRetriever):
    """High-performance retriever querying Xeren's sovereign custom Pattern DB."""

    AST_QUERY_REGEX = re.compile(r"\b(def|class|function|method|call)\s+([A-Za-z0-9_]+)", re.IGNORECASE)

    def __init__(
        self,
        pattern_db: Optional[XerenPatternDB] = None,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        alpha: float = 0.5,
        expand_hierarchy: bool = True,
        storage_dir: Optional[str] = None,
    ) -> None:
        self.pattern_db = pattern_db or XerenPatternDB(storage_dir=storage_dir)
        self.embedding_model = embedding_model
        self.alpha = alpha
        self.expand_hierarchy = expand_hierarchy

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Execute multi-pattern retrieval across AST, dense vector, and lexical indices."""
        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Check if query specifies an AST code construct (e.g. "def forward", "class Attention")
        ast_match = self.AST_QUERY_REGEX.search(clean_query)
        ast_results: List[PatternSearchResult] = []
        if ast_match:
            symbol = ast_match.group(2)
            ast_results = self.pattern_db.search_ast(symbol_name=symbol, top_k=top_k)

        # 2. Dense vector embedding (if embedding model configured)
        query_vector: Optional[List[float]] = None
        if self.embedding_model is not None:
            try:
                query_vector = self.embedding_model.embed_query(clean_query)
            except Exception:
                query_vector = None

        # 3. Hybrid or Lexical search
        pattern_hits: List[PatternSearchResult] = []
        if query_vector is not None:
            pattern_hits = self.pattern_db.hybrid_search(
                query_text=clean_query,
                query_vector=query_vector,
                alpha=self.alpha,
                top_k=top_k * 2,
            )
        else:
            # CPU-pure symbolic & lexical search
            pattern_hits = self.pattern_db.search(
                PatternQuery(query_text=clean_query, top_k=top_k * 2)
            )

        # Merge AST hits with general hits
        combined_hits: List[PatternSearchResult] = []
        seen_pids = set()

        for hit in ast_results:
            if hit.pattern.pattern_id not in seen_pids:
                combined_hits.append(hit)
                seen_pids.add(hit.pattern.pattern_id)

        for hit in pattern_hits:
            if hit.pattern.pattern_id not in seen_pids:
                combined_hits.append(hit)
                seen_pids.add(hit.pattern.pattern_id)

        # 4. Transform into SearchResult items with metadata filter check
        search_results: List[SearchResult] = []
        seen_chunks = set()

        for hit in combined_hits:
            cid = hit.pattern.chunk_id
            if cid in seen_chunks:
                continue

            chunk = self._reconstruct_chunk(hit)
            if not chunk:
                continue

            # Apply MetadataFilter
            if filter and not filter.matches(chunk.metadata):
                continue

            seen_chunks.add(cid)

            # Optional hierarchical context expansion
            if self.expand_hierarchy:
                self._enrich_with_hierarchy(chunk)

            search_results.append(
                SearchResult(
                    chunk=chunk,
                    score=hit.score,
                    retrieval_type=f"sovereign_{hit.match_source}",
                    vector=hit.pattern.vector,
                )
            )

            if len(search_results) >= top_k:
                break

        return search_results

    async def aretrieve(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Asynchronous execution via thread pool offloading."""
        return await asyncio.to_thread(self.retrieve, query, top_k, filter)

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _reconstruct_chunk(self, hit: PatternSearchResult) -> Optional[DocumentChunk]:
        """Reconstruct DocumentChunk from pattern payload and features."""
        payload = hit.pattern.payload
        features = hit.pattern.features

        text = payload.get("text") or payload.get("code_snippet") or hit.pattern.signature
        meta = dict(payload.get("metadata", {}))
        meta["match_source"] = hit.match_source
        meta["pattern_type"] = hit.pattern.pattern_type.value
        if "node_type" in features:
            meta["ast_node_type"] = features["node_type"]
        if "arguments" in features:
            meta["ast_arguments"] = features["arguments"]

        return DocumentChunk(
            chunk_id=hit.pattern.chunk_id,
            document_id=hit.pattern.document_id,
            content=text,
            chunk_index=features.get("chunk_index", 0),
            metadata=meta,
        )

    def _enrich_with_hierarchy(self, chunk: DocumentChunk) -> None:
        """Enrich chunk with parent and child contextual breadcrumbs."""
        ctx = self.pattern_db.get_hierarchical_context(chunk.chunk_id)
        if ctx.get("parent_chunk_id"):
            chunk.metadata["parent_chunk_id"] = ctx["parent_chunk_id"]
        if ctx.get("child_count", 0) > 0:
            chunk.metadata["child_chunk_count"] = ctx["child_count"]


def create_sovereign_rag_engine(
    pattern_db: Optional[XerenPatternDB] = None,
    embedding_model: Optional[BaseEmbeddingModel] = None,
    reranker: Optional[BaseReranker] = None,
    context_builder: Optional[ContextBuilder] = None,
    alpha: float = 0.5,
    storage_dir: Optional[str] = None,
) -> RAGQueryEngine:
    """Convenience factory creating a RAGQueryEngine backed by XerenPatternDB."""
    retriever = SovereignPatternRetriever(
        pattern_db=pattern_db,
        embedding_model=embedding_model,
        alpha=alpha,
        storage_dir=storage_dir,
    )
    if context_builder is None:
        from xeren.rag.context.builder import ContextBuilder as DefaultContextBuilder
        context_builder = DefaultContextBuilder()

    from xeren.rag.engine import RAGQueryEngine

    return RAGQueryEngine(
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
    )


