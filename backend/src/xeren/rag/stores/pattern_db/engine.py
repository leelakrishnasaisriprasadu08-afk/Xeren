"""Xeren Sovereign Pattern Database (RAG Pipeline Only).

A zero-daemon, high-performance local database engine tailored specifically
for storing, indexing, and retrieving complex patterns for RAG knowledge pipelines:
- Dense vector patterns (cosine similarity on CPU)
- Sparse lexical & token patterns
- Code AST patterns (functions, classes, calls, arguments)
- Hierarchical document trees (parent-child section mapping)
- Faceted metadata attributes

Strict Isolation:
RAG knowledge patterns only. Rejects user PII, credentials, and session data.
"""

import ast
from collections import defaultdict
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from xeren.rag.document import DocumentChunk
from xeren.rag.stores.pattern_db.corners import (
    CornerQueryResult,
    MultiCornerPatternStore,
    PatternCorner,
    PatternCornerEvaluator,
    ThreeFormRecord,
)
from xeren.rag.stores.pattern_db.indexer import PatternIndexer
from xeren.rag.stores.pattern_db.schema import (
    PatternQuery,
    PatternRecord,
    PatternSearchResult,
    PatternType,
    SecurityIsolationError,
)
from xeren.rag.stores.pattern_db.storage_engine import PatternStorageEngine


class XerenPatternDB:
    """Core sovereign pattern database manager for Xeren RAG."""

    def __init__(self, storage_dir: Optional[str] = None, auto_persist: bool = False) -> None:
        self.storage_dir = storage_dir
        self.auto_persist = auto_persist
        self._lock = threading.RLock()
        self._indexer = PatternIndexer()
        self._corner_store = MultiCornerPatternStore()
        self._storage: Optional[PatternStorageEngine] = (
            PatternStorageEngine(storage_dir) if storage_dir else None
        )

        if self._storage:
            self.load()

    # -------------------------------------------------------------------------
    # Ingestion & Registration
    # -------------------------------------------------------------------------

    def add_pattern(self, record: PatternRecord) -> str:
        """Register a single pattern record into the database."""
        with self._lock:
            # Enforce RAG pipeline security isolation
            record.verify_rag_pipeline_isolation()
            self._indexer.index_record(record)
            if self.auto_persist and self._storage:
                self.persist()
            return record.pattern_id

    def add_patterns(self, records: List[PatternRecord]) -> List[str]:
        """Register a batch of pattern records."""
        with self._lock:
            ids = []
            for rec in records:
                rec.verify_rag_pipeline_isolation()
                self._indexer.index_record(rec)
                ids.append(rec.pattern_id)
            if self.auto_persist and self._storage:
                self.persist()
            return ids

    def ingest_chunk_patterns(
        self,
        chunk: DocumentChunk,
        vector: Optional[List[float]] = None,
    ) -> List[PatternRecord]:
        """Automatically decompose and store complex patterns from a DocumentChunk."""
        with self._lock:
            records: List[PatternRecord] = []

            # 1. Dense Vector Pattern (if embedding vector provided)
            if vector is not None and len(vector) > 0:
                dense_rec = PatternRecord(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    pattern_type=PatternType.DENSE_VECTOR,
                    signature=chunk.content[:120].strip(),
                    features={
                        "chunk_index": chunk.chunk_index,
                        "character_count": chunk.character_count,
                        "token_count": chunk.token_count,
                        "dimension": len(vector),
                    },
                    vector=vector,
                    payload={"text": chunk.content, "metadata": chunk.metadata},
                )
                records.append(dense_rec)

            # 2. Sparse Lexical Pattern
            sparse_rec = PatternRecord(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                pattern_type=PatternType.SPARSE_LEXICAL,
                signature=chunk.content[:200].strip(),
                features={
                    "chunk_index": chunk.chunk_index,
                    "source": chunk.metadata.get("source", "unknown"),
                },
                sparse_weights=self._extract_term_frequencies(chunk.content),
                payload={"text": chunk.content, "metadata": chunk.metadata},
            )
            records.append(sparse_rec)

            # 3. Hierarchical Pattern
            parent_id = chunk.metadata.get("parent_chunk_id") or chunk.metadata.get("parent_id")
            hierarchical_rec = PatternRecord(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                pattern_type=PatternType.HIERARCHICAL,
                signature=f"doc:{chunk.document_id}:chunk:{chunk.chunk_index}",
                features={
                    "parent_chunk_id": parent_id,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "section": chunk.metadata.get("section", ""),
                    "header_path": chunk.metadata.get("header_path", []),
                },
                payload={"text": chunk.content, "metadata": chunk.metadata},
            )
            records.append(hierarchical_rec)

            # 4. Code AST Pattern (if content is Python code)
            ast_patterns = self._extract_ast_patterns(chunk)
            records.extend(ast_patterns)

            # 5. Faceted Metric Pattern
            faceted_rec = PatternRecord(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                pattern_type=PatternType.FACETED_METRIC,
                signature=f"meta:{chunk.chunk_id}",
                features={
                    "doc_type": chunk.metadata.get("doc_type", "text"),
                    "source": chunk.metadata.get("source", ""),
                    "language": chunk.metadata.get("language", "text"),
                    "category": chunk.metadata.get("category", ""),
                    **{k: v for k, v in chunk.metadata.items() if isinstance(v, (str, int, float, bool))},
                },
                payload={"text": chunk.content, "metadata": chunk.metadata},
            )
            records.append(faceted_rec)

            # Index all generated patterns
            self.add_patterns(records)
            return records

    # -------------------------------------------------------------------------
    # Multi-Pattern Retrieval
    # -------------------------------------------------------------------------

    def search(self, query: PatternQuery) -> List[PatternSearchResult]:
        """Execute a multi-pattern search matching the query specifications."""
        with self._lock:
            # Step 1: Pre-filter by facets if specified
            candidate_ids: Optional[Set[str]] = None
            if query.facets:
                candidate_ids = self._indexer.filter_facets(query.facets)
                if not candidate_ids:
                    return []

            # Step 2: AST code symbol search
            if query.symbol_name or query.ast_node_type:
                ast_records = self._indexer.search_ast(
                    symbol_name=query.symbol_name,
                    node_type=query.ast_node_type,
                    candidate_ids=candidate_ids,
                )
                return [
                    PatternSearchResult(
                        pattern=rec,
                        score=1.0,
                        match_source="ast",
                        explanation=f"Matched AST symbol '{query.symbol_name}' / type '{query.ast_node_type}'",
                    )
                    for rec in ast_records[: query.top_k]
                ]

            # Step 3: Dense vector search
            if query.query_vector is not None and len(query.query_vector) > 0 and not query.query_text:
                dense_results = self._indexer.search_dense(
                    query_vector=query.query_vector,
                    top_k=query.top_k,
                    candidate_ids=candidate_ids,
                )
                return [
                    PatternSearchResult(
                        pattern=rec,
                        score=score,
                        match_source="dense",
                        explanation="Vector cosine similarity",
                    )
                    for rec, score in dense_results
                ]

            # Step 4: Lexical search
            if query.query_text and query.query_vector is None:
                lex_results = self._indexer.search_lexical(
                    query_text=query.query_text,
                    top_k=query.top_k,
                    candidate_ids=candidate_ids,
                )
                return [
                    PatternSearchResult(
                        pattern=rec,
                        score=score,
                        match_source="sparse",
                        explanation="Sparse token frequency matching",
                    )
                    for rec, score in lex_results
                ]

            # Step 5: Hybrid search (combining dense vector + lexical query)
            if query.query_text and query.query_vector is not None:
                return self.hybrid_search(
                    query_text=query.query_text,
                    query_vector=query.query_vector,
                    alpha=query.alpha,
                    top_k=query.top_k,
                    candidate_ids=candidate_ids,
                )

            # Step 6: Hierarchical parent query
            if query.parent_chunk_id:
                children = self._indexer.get_children(query.parent_chunk_id)
                return [
                    PatternSearchResult(
                        pattern=rec,
                        score=1.0,
                        match_source="hierarchy",
                        explanation=f"Child chunk of parent {query.parent_chunk_id}",
                    )
                    for rec in children[: query.top_k]
                ]

            return []

    def hybrid_search(
        self,
        query_text: str,
        query_vector: Optional[List[float]] = None,
        alpha: float = 0.5,
        top_k: int = 5,
        candidate_ids: Optional[Set[str]] = None,
    ) -> List[PatternSearchResult]:
        """Perform hybrid retrieval blending dense semantic and sparse lexical patterns."""
        with self._lock:
            dense_map: Dict[str, Tuple[PatternRecord, float]] = {}
            lexical_map: Dict[str, Tuple[PatternRecord, float]] = {}

            if query_vector is not None and len(query_vector) > 0:
                dense_hits = self._indexer.search_dense(
                    query_vector=query_vector,
                    top_k=top_k * 3,
                    candidate_ids=candidate_ids,
                )
                dense_map = {rec.chunk_id: (rec, score) for rec, score in dense_hits}

            if query_text:
                lex_hits = self._indexer.search_lexical(
                    query_text=query_text,
                    top_k=top_k * 3,
                    candidate_ids=candidate_ids,
                )
                lexical_map = {rec.chunk_id: (rec, score) for rec, score in lex_hits}

            # Normalization
            dense_max = max((s for _, s in dense_map.values()), default=1.0) or 1.0
            lex_max = max((s for _, s in lexical_map.values()), default=1.0) or 1.0

            all_chunk_ids = set(dense_map.keys()).union(set(lexical_map.keys()))
            scored_patterns: List[Tuple[PatternRecord, float, str]] = []

            for cid in all_chunk_ids:
                d_rec, d_raw = dense_map.get(cid, (None, 0.0))
                l_rec, l_raw = lexical_map.get(cid, (None, 0.0))

                norm_dense = max(0.0, d_raw) / dense_max
                norm_lex = max(0.0, l_raw) / lex_max

                combined_score = (alpha * norm_dense) + ((1.0 - alpha) * norm_lex)
                rec = d_rec or l_rec
                if rec:
                    source_tag = "hybrid"
                    if d_raw > 0 and l_raw == 0:
                        source_tag = "dense"
                    elif l_raw > 0 and d_raw == 0:
                        source_tag = "sparse"
                    scored_patterns.append((rec, combined_score, source_tag))

            scored_patterns.sort(key=lambda x: x[1], reverse=True)

            return [
                PatternSearchResult(
                    pattern=rec,
                    score=score,
                    match_source=src,
                    explanation=f"Hybrid blend (alpha={alpha}) score={score:.4f}",
                )
                for rec, score, src in scored_patterns[:top_k]
            ]

    def search_ast(
        self,
        symbol_name: Optional[str] = None,
        node_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[PatternSearchResult]:
        """Convenience method for searching code AST symbol patterns."""
        query = PatternQuery(
            symbol_name=symbol_name,
            ast_node_type=node_type,
            pattern_types=[PatternType.CODE_AST],
            top_k=top_k,
        )
        return self.search(query)

    def get_hierarchical_context(self, chunk_id: str) -> Dict[str, Any]:
        """Retrieve contextual tree patterns (parent chunk and child chunks) for a chunk."""
        with self._lock:
            parent_id = self._indexer.get_parent_id(chunk_id)
            children = self._indexer.get_children(chunk_id)
            chunk_patterns = self._indexer.get_chunk_patterns(chunk_id)

            return {
                "chunk_id": chunk_id,
                "parent_chunk_id": parent_id,
                "child_count": len(children),
                "children": [c.model_dump() for c in children],
                "patterns": [p.model_dump() for p in chunk_patterns],
            }

    # -------------------------------------------------------------------------
    # Management & Deletion
    # -------------------------------------------------------------------------

    def delete_chunk(self, chunk_id: str) -> int:
        """Delete all pattern records belonging to a chunk ID."""
        with self._lock:
            patterns = self._indexer.get_chunk_patterns(chunk_id)
            deleted = 0
            for p in list(patterns):
                if self._indexer.remove_record(p.pattern_id):
                    deleted += 1
            if self.auto_persist and self._storage:
                self.persist()
            return deleted

    def delete_patterns(self, pattern_ids: List[str]) -> int:
        """Delete specific pattern records by their IDs."""
        with self._lock:
            deleted = 0
            for pid in pattern_ids:
                if self._indexer.remove_record(pid):
                    deleted += 1
            if self.auto_persist and self._storage:
                self.persist()
            return deleted

    def count(self) -> int:
        """Total number of patterns in the database."""
        with self._lock:
            return len(self._indexer.records)

    def clear(self) -> None:
        """Wipe all patterns from memory and storage."""
        with self._lock:
            self._indexer.clear()
            if self._storage:
                self._storage.clear()

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def persist(self) -> Dict[str, Any]:
        """Persist database contents atomically to disk."""
        with self._lock:
            if not self._storage:
                raise ValueError("Storage directory not configured for this XerenPatternDB instance.")
            return self._storage.persist(self._indexer.records)

    def load(self) -> int:
        """Load database contents from disk."""
        with self._lock:
            if not self._storage:
                return 0
            records = self._storage.load()
            self._indexer.clear()
            for r in records.values():
                self._indexer.index_record(r)
            return len(records)

    def stats(self) -> Dict[str, Any]:
        """Summary diagnostics of pattern distributions."""
        with self._lock:
            type_counts: Dict[str, int] = defaultdict(int)
            for rec in self._indexer.records.values():
                type_counts[rec.pattern_type.value] += 1
            return {
                "total_patterns": len(self._indexer.records),
                "dense_vectors_indexed": len(self._indexer._dense_ids),
                "pattern_type_distribution": dict(type_counts),
                "storage_directory": str(self.storage_dir) if self.storage_dir else "memory_only",
            }

    # -------------------------------------------------------------------------
    # Internal Pattern Extractors
    # -------------------------------------------------------------------------

    def _extract_ast_patterns(self, chunk: DocumentChunk) -> List[PatternRecord]:
        """Safely parse Python code AST and generate structural pattern records."""
        content = chunk.content.strip()
        # Heuristic check: is it code or marked python?
        lang = chunk.metadata.get("language", "").lower()
        is_code = lang in ("python", "py") or any(
            kw in content for kw in ("def ", "class ", "import ", "return ", "async def ")
        )
        if not is_code:
            return []

        try:
            tree = ast.parse(content)
        except Exception:
            # Not valid standalone Python code; skip AST parsing safely
            return []

        ast_records: List[PatternRecord] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                sig = f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({', '.join(args)})"
                ast_records.append(
                    PatternRecord(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        pattern_type=PatternType.CODE_AST,
                        signature=node.name,
                        features={
                            "node_type": "FunctionDef",
                            "full_signature": sig,
                            "arguments": args,
                            "line_number": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef),
                        },
                        payload={
                            "code_snippet": content,
                            "symbol": node.name,
                            "metadata": chunk.metadata,
                        },
                    )
                )

            elif isinstance(node, ast.ClassDef):
                bases = [
                    base.id if isinstance(base, ast.Name) else "Unknown"
                    for base in node.bases
                ]
                ast_records.append(
                    PatternRecord(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        pattern_type=PatternType.CODE_AST,
                        signature=node.name,
                        features={
                            "node_type": "ClassDef",
                            "bases": bases,
                            "line_number": node.lineno,
                        },
                        payload={
                            "code_snippet": content,
                            "symbol": node.name,
                            "metadata": chunk.metadata,
                        },
                    )
                )

            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                # Function invocation pattern
                ast_records.append(
                    PatternRecord(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        pattern_type=PatternType.CODE_AST,
                        signature=node.func.id,
                        features={
                            "node_type": "Call",
                            "call_target": node.func.id,
                            "line_number": node.lineno,
                        },
                        payload={
                            "code_snippet": content,
                            "symbol": node.func.id,
                            "metadata": chunk.metadata,
                        },
                    )
                )

        return ast_records

    @staticmethod
    def _extract_term_frequencies(text: str) -> Dict[str, float]:
        """Compute term frequencies for sparse lexical weighting."""
        import re
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        if not tokens:
            return {}
        counts: Dict[str, int] = defaultdict(int)
        for t in tokens:
            if len(t) > 1:
                counts[t] += 1
        total = float(len(tokens))
        return {k: round(v / total, 4) for k, v in counts.items()}

    # -------------------------------------------------------------------------
    # Multi-Corner Pattern Architecture
    # -------------------------------------------------------------------------

    @property
    def corner_store(self) -> MultiCornerPatternStore:
        """Access the partitioned multi-corner pattern store."""
        return self._corner_store

    def ingest_corner_pattern(
        self,
        corner: PatternCorner,
        raw_data: Dict[str, Any],
        summary: str,
        success: bool = True,
        ttl_seconds: Optional[float] = None,
        agent_id: Optional[str] = None,
        parent_workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ThreeFormRecord:
        """Store a structured pattern in Three-Form format into its specialized corner."""
        with self._lock:
            return self._corner_store.ingest_pattern(
                corner=corner,
                raw_data=raw_data,
                summary=summary,
                success=success,
                ttl_seconds=ttl_seconds,
                agent_id=agent_id,
                parent_workflow_id=parent_workflow_id,
                metadata=metadata,
            )

    def query_corners(
        self,
        query_text: str,
        top_k: int = 5,
        target_corner: Optional[PatternCorner] = None,
        tenant_filter: Optional[str] = None,
    ) -> List[CornerQueryResult]:
        """Query partitioned pattern corners with routing, coarse-to-fine match, and trust reranking."""
        with self._lock:
            return self._corner_store.query(
                query_text=query_text,
                top_k=top_k,
                target_corner=target_corner,
                tenant_filter=tenant_filter,
            )

    def evaluate_corners(self) -> Dict[str, Any]:
        """Run golden diagnostic evaluation across all corners to identify failing partitions."""
        return PatternCornerEvaluator.evaluate_store(self._corner_store)

