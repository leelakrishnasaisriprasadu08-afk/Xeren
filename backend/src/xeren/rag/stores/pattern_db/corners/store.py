"""
Xeren Sovereign Pattern DB — Multi-Corner Pattern Storage Engine
================================================================
Specialized, partitioned pattern store implementing coarse-to-fine search,
template compression for repeated patterns, and trust-biased reranking.
"""

from __future__ import annotations

from collections import defaultdict
import math
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import CornerQueryResult, PatternCorner, ThreeFormRecord
from .normalizer import PatternSignatureNormalizer
from .router import PatternQueryRouter


class MultiCornerPatternStore:
    """Sovereign multi-corner pattern database storing records in 3 forms with custom corner retrieval."""

    def __init__(self, embedder_fn: Optional[Callable[[str], List[float]]] = None) -> None:
        self.embedder_fn = embedder_fn
        self._lock = threading.RLock()

        # Partitioned storage: corner -> list of ThreeFormRecords
        self._partitions: Dict[PatternCorner, List[ThreeFormRecord]] = {
            c: [] for c in PatternCorner
        }
        # Signature Template Compression registry: (corner, signature) -> template record
        self._template_registry: Dict[Tuple[PatternCorner, str], ThreeFormRecord] = {}

        # Inverted lexical tokens per corner: corner -> token -> list of (record_id, weight)
        self._lexical_index: Dict[PatternCorner, Dict[str, List[Tuple[str, float]]]] = {
            c: defaultdict(list) for c in PatternCorner
        }

        # Parent workflow lookup: workflow_id -> workflow record
        self._workflows: Dict[str, ThreeFormRecord] = {}

    # -------------------------------------------------------------------------
    # Ingestion & Compression
    # -------------------------------------------------------------------------

    def ingest_pattern(
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
        """
        Store a pattern in Three-Form format (Raw, Signature, Summary/doc2query).
        Applies signature compression to merge repeated runs into canonical templates.
        """
        with self._lock:
            # 1. Extract structural signature
            signature = PatternSignatureNormalizer.extract_signature(corner, raw_data)

            # 2. Check for existing template compression
            key = (corner, signature)
            if key in self._template_registry:
                existing = self._template_registry[key]
                if success:
                    existing.success_count += 1
                else:
                    existing.failure_count += 1
                # Update latest raw instance parameters
                existing.raw = raw_data
                existing.metadata.update(metadata or {})
                return existing

            # 3. Generate doc2query questions (what users will ask)
            doc2query = PatternSignatureNormalizer.generate_doc2query(corner, raw_data, summary)

            # 4. Generate dense embedding on what people will ask (not just raw data)
            vector: Optional[List[float]] = None
            if corner not in (PatternCorner.RULES_PERMISSIONS, PatternCorner.ENTITY_STATE):
                if self.embedder_fn:
                    embed_text = f"{summary} " + " ".join(doc2query[:3])
                    vector = self.embedder_fn(embed_text)

            pattern_id = f"pat-{corner.value[:4]}-{signature[:8]}-{int(time.time()*1000)%100000}"
            record = ThreeFormRecord(
                pattern_id=pattern_id,
                corner=corner,
                raw=raw_data,
                signature=signature,
                summary_text=summary,
                doc2query_questions=doc2query,
                vector=vector,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                created_at=time.time(),
                ttl_seconds=ttl_seconds,
                agent_id=agent_id,
                parent_workflow_id=parent_workflow_id,
                metadata=metadata or {},
            )

            # Register in partition & template index
            self._partitions[corner].append(record)
            self._template_registry[key] = record

            if corner == PatternCorner.WORKFLOW:
                self._workflows[pattern_id] = record

            # Index lexical tokens for BM25
            self._index_lexical(record)
            return record

    def _index_lexical(self, record: ThreeFormRecord) -> None:
        """Index searchable terms into corner-specific inverted index."""
        searchable_text = f"{record.summary_text} {record.signature} " + " ".join(record.doc2query_questions)
        tokens = [t.lower() for t in searchable_text.split() if len(t) >= 2]
        token_counts: Dict[str, int] = defaultdict(int)
        for t in tokens:
            token_counts[t] += 1

        for token, count in token_counts.items():
            self._lexical_index[record.corner][token].append((record.pattern_id, float(count)))

    # -------------------------------------------------------------------------
    # Multi-Corner Query & Retrieval
    # -------------------------------------------------------------------------

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        target_corner: Optional[PatternCorner] = None,
        tenant_filter: Optional[str] = None,
    ) -> List[CornerQueryResult]:
        """
        Unified multi-corner query:
        1. Route to targeted corners (if not explicitly specified)
        2. Execute coarse-to-fine search per corner
        3. Merge candidate hits with trust-weighted reranking
        """
        with self._lock:
            if target_corner:
                routes = [(target_corner, 1.0)]
            else:
                routes = PatternQueryRouter.route(query_text)

            query_vector: Optional[List[float]] = None
            if self.embedder_fn:
                query_vector = self.embedder_fn(query_text)

            all_results: List[CornerQueryResult] = []

            for corner, route_weight in routes[:3]:
                corner_results = self._search_corner(
                    corner=corner,
                    query_text=query_text,
                    query_vector=query_vector,
                    top_k=top_k,
                    tenant_filter=tenant_filter,
                )
                for res in corner_results:
                    # Apply route confidence weight
                    res.score *= route_weight
                    all_results.append(res)

            # Sort and deduplicate by pattern_id
            seen_ids: set[str] = set()
            ranked_results: List[CornerQueryResult] = []
            all_results.sort(key=lambda x: x.score, reverse=True)

            for r in all_results:
                if r.record.pattern_id not in seen_ids:
                    seen_ids.add(r.record.pattern_id)
                    ranked_results.append(r)
                if len(ranked_results) >= top_k:
                    break

            return ranked_results

    def _search_corner(
        self,
        corner: PatternCorner,
        query_text: str,
        query_vector: Optional[List[float]],
        top_k: int,
        tenant_filter: Optional[str],
    ) -> List[CornerQueryResult]:
        """Custom retrieval logic tailored to the physics of each corner."""
        records = [r for r in self._partitions[corner] if not r.is_expired()]
        if tenant_filter:
            records = [r for r in records if r.metadata.get("tenant") == tenant_filter]

        if not records:
            return []

        results: List[CornerQueryResult] = []

        # CORNER 1: Rules & Permissions -> Exact lookup, zero vectors
        if corner == PatternCorner.RULES_PERMISSIONS:
            for r in records:
                sig_match = r.signature.lower() in query_text.lower()
                action_words = [w for w in r.raw.get("action", "").lower().split() if len(w) >= 3]
                subj_match = any(word in query_text.lower() for word in action_words)
                res_match = bool(r.raw.get("resource")) and r.raw.get("resource", "").lower() in query_text.lower()
                summary_match = any(w in query_text.lower() for w in r.summary_text.lower().split() if len(w) >= 4)
                if sig_match or subj_match or res_match or summary_match:
                    score = 1.0 if sig_match else (0.90 if (subj_match and res_match) else 0.85)
                    results.append(CornerQueryResult(
                        record=r, corner=corner, score=score,
                        retrieval_method="exact", matched_signature=sig_match,
                    ))

        # CORNER 2: Entity State -> Relational key match, zero vectors
        elif corner == PatternCorner.ENTITY_STATE:
            for r in records:
                key_match = any(v in query_text for v in r.raw.values() if isinstance(v, str))
                if key_match:
                    results.append(CornerQueryResult(
                        record=r, corner=corner, score=0.95, retrieval_method="exact",
                    ))

        # CORNER 3: Tool Schemas -> Exact name match + BM25
        elif corner == PatternCorner.TOOL_SCHEMA:
            for r in records:
                tool_name = r.raw.get("name", "").lower()
                if tool_name and tool_name in query_text.lower():
                    results.append(CornerQueryResult(
                        record=r, corner=corner, score=1.0, retrieval_method="exact",
                    ))
                else:
                    bm25_score = self._compute_bm25_score(corner, r.pattern_id, query_text)
                    if bm25_score > 0.1:
                        results.append(CornerQueryResult(
                            record=r, corner=corner, score=min(0.9, bm25_score), retrieval_method="bm25",
                        ))

        # CORNER 4: Failure Fix -> BM25 on error string first, dense vector second
        elif corner == PatternCorner.FAILURE_FIX:
            for r in records:
                err_text = r.raw.get("error", "")
                bm25_score = self._compute_bm25_score(corner, r.pattern_id, query_text)
                vec_sim = self._cosine_similarity(query_vector, r.vector) if (query_vector and r.vector) else 0.0

                # BM25 is primary (0.65), vector is secondary (0.35)
                combined = 0.65 * min(1.0, bm25_score) + 0.35 * vec_sim
                trust_boost = r.trust_score * 0.15
                final_score = combined + trust_boost

                if final_score > 0.15:
                    results.append(CornerQueryResult(
                        record=r, corner=corner, score=final_score,
                        retrieval_method="hybrid_bm25_primary",
                    ))

        # CORNER 5: Workflow & Intent -> Vector on doc2query + parent expansion
        elif corner in (PatternCorner.WORKFLOW, PatternCorner.INTENT_SOLUTION):
            for r in records:
                vec_sim = self._cosine_similarity(query_vector, r.vector) if (query_vector and r.vector) else 0.0
                bm25 = self._compute_bm25_score(corner, r.pattern_id, query_text)
                sim = max(vec_sim, min(1.0, bm25))

                trust_boost = r.trust_score * 0.20
                final_score = sim + trust_boost

                # Parent expansion
                parent_wf: Optional[Dict[str, Any]] = None
                if r.parent_workflow_id and r.parent_workflow_id in self._workflows:
                    parent_wf = self._workflows[r.parent_workflow_id].raw

                if final_score > 0.15:
                    results.append(CornerQueryResult(
                        record=r, corner=corner, score=final_score,
                        retrieval_method="vector_doc2query",
                        parent_workflow=parent_wf,
                    ))

        # CORNER 6: Episodic Memory -> Recency time decay + similarity
        elif corner == PatternCorner.EPISODIC_MEMORY:
            now = time.time()
            for r in records:
                vec_sim = self._cosine_similarity(query_vector, r.vector) if (query_vector and r.vector) else 0.5
                age_hours = (now - r.created_at) / 3600.0
                recency_weight = math.exp(-0.05 * age_hours)  # Time decay factor
                score = 0.7 * vec_sim + 0.3 * recency_weight
                results.append(CornerQueryResult(
                    record=r, corner=corner, score=score, retrieval_method="recency_similarity",
                ))

        # Default fallback (Volatile Web, Execution Trace)
        else:
            for r in records:
                bm25 = self._compute_bm25_score(corner, r.pattern_id, query_text)
                vec_sim = self._cosine_similarity(query_vector, r.vector) if (query_vector and r.vector) else 0.0
                score = 0.5 * bm25 + 0.5 * vec_sim
                if score > 0.1:
                    results.append(CornerQueryResult(
                        record=r, corner=corner, score=score, retrieval_method="hybrid",
                    ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _compute_bm25_score(self, corner: PatternCorner, record_id: str, query: str) -> float:
        """Lightweight BM25 term frequency match within corner partition."""
        tokens = [t.lower() for t in query.split() if len(t) >= 2]
        score = 0.0
        corner_lex = self._lexical_index.get(corner, {})

        for t in tokens:
            if t in corner_lex:
                for rid, freq in corner_lex[t]:
                    if rid == record_id:
                        # Normalized tf
                        score += math.log(1.0 + freq)
        return min(1.0, score / max(1.0, float(len(tokens))))

    @staticmethod
    def _cosine_similarity(v1: Optional[List[float]], v2: Optional[List[float]]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        if n1 == 0.0 or n2 == 0.0:
            return 0.0
        return max(0.0, dot / (n1 * n2))
