"""Memory-Augmented Generation (MAG) retrieval engine for Xeren."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set

from xeren.rag.mag.types import (
    MemoryQuery,
    MemoryRecord,
    MemoryTier,
    RetrievedMemory,
)

logger = logging.getLogger("xeren.rag.mag")


class MAGRetrievalEngine:
    """Cognitive Memory-Augmented Generation engine.

    Maintains three memory tiers (Working, Episodic, Semantic) and retrieves relevant
    context scored by relevance, intrinsic importance, and exponential recency decay.
    """

    def __init__(
        self,
        time_provider: Optional[Callable[[], float]] = None,
        default_half_life_hours: float = 72.0,
    ) -> None:
        self._time = time_provider or time.time
        self.default_half_life_hours = default_half_life_hours

        # In-memory storage of memory records keyed by memory_id
        self._records: Dict[str, MemoryRecord] = {}

        # Secondary indices
        self._tier_index: Dict[MemoryTier, Set[str]] = {
            MemoryTier.WORKING: set(),
            MemoryTier.EPISODIC: set(),
            MemoryTier.SEMANTIC: set(),
        }
        self._session_index: Dict[str, Set[str]] = {}

    def remember(
        self,
        content: str,
        tier: MemoryTier = MemoryTier.EPISODIC,
        importance: float = 0.5,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        """Store a new cognitive memory record."""
        cleaned = content.strip()
        if not cleaned:
            raise ValueError("Memory content cannot be empty.")

        importance = max(0.0, min(1.0, float(importance)))
        now = self._time()

        # Deterministic ID generation based on content and tier
        digest = hashlib.sha256(f"{tier.value}:{session_id or ''}:{cleaned}".encode("utf-8")).hexdigest()[:16]
        mem_id = f"mem_{tier.value[:3]}_{digest}"

        if mem_id in self._records:
            # Update existing memory with fresh timestamp and highest importance
            existing = self._records[mem_id]
            existing.last_accessed_at = now
            existing.importance = max(existing.importance, importance)
            if tags:
                existing.tags = list(set(existing.tags + tags))
            if metadata:
                existing.metadata.update(metadata)
            return existing

        record = MemoryRecord(
            memory_id=mem_id,
            tier=tier,
            content=cleaned,
            importance=importance,
            session_id=session_id,
            created_at=now,
            last_accessed_at=now,
            access_count=0,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._records[mem_id] = record
        self._tier_index[tier].add(mem_id)
        if session_id:
            self._session_index.setdefault(session_id, set()).add(mem_id)

        logger.debug("MAG stored memory record [%s] tier=%s importance=%.2f", mem_id, tier.value, importance)
        return record

    def record_working_constraint(
        self,
        constraint: str,
        session_id: Optional[str] = None,
    ) -> MemoryRecord:
        """Convenience helper to record an active session constraint in WORKING memory."""
        return self.remember(
            content=constraint,
            tier=MemoryTier.WORKING,
            importance=0.9,
            session_id=session_id,
            tags=["constraint", "active_goal"],
        )

    def record_user_correction(
        self,
        correction: str,
        session_id: Optional[str] = None,
    ) -> MemoryRecord:
        """Convenience helper to record a direct user correction in EPISODIC memory with high weight."""
        return self.remember(
            content=correction,
            tier=MemoryTier.EPISODIC,
            importance=1.0,
            session_id=session_id,
            tags=["user_feedback", "correction", "high_priority"],
        )

    def record_semantic_fact(
        self,
        fact: str,
        importance: float = 0.8,
        tags: Optional[List[str]] = None,
    ) -> MemoryRecord:
        """Convenience helper to record an enduring entity fact or preference in SEMANTIC memory."""
        return self.remember(
            content=fact,
            tier=MemoryTier.SEMANTIC,
            importance=importance,
            tags=(tags or []) + ["semantic_fact"],
        )

    def retrieve(self, query: MemoryQuery) -> List[RetrievedMemory]:
        """Retrieve memories matching query and ranked by cognitive score."""
        target_tiers = set(query.tiers) if query.tiers else set(MemoryTier)
        now = self._time()

        tokens = self._tokenize(query.query_text)
        candidates: List[RetrievedMemory] = []

        # Candidate selection by tier
        candidate_ids: Set[str] = set()
        for tier in target_tiers:
            candidate_ids.update(self._tier_index.get(tier, set()))

        for mem_id in candidate_ids:
            record = self._records.get(mem_id)
            if not record:
                continue

            # If working memory has a session_id filter, restrict to that session
            if record.tier == MemoryTier.WORKING and query.session_id:
                if record.session_id != query.session_id:
                    continue

            # Calculate relevance score (lexical overlap + tag bonuses)
            relevance = self._calculate_relevance(tokens, record)
            if relevance <= 0.0:
                continue

            # Calculate recency decay
            recency = record.compute_decay_factor(
                current_time=now,
                half_life_hours=query.half_life_hours,
            )

            # Cognitive score formula: relevance * importance * recency
            cognitive_score = relevance * record.importance * recency

            if cognitive_score >= query.min_score:
                candidates.append(
                    RetrievedMemory(
                        record=record,
                        score=cognitive_score,
                        relevance=relevance,
                        recency_factor=recency,
                        importance=record.importance,
                    )
                )

        # Sort descending by cognitive score
        candidates.sort(key=lambda item: item.score, reverse=True)
        selected = candidates[: query.limit]

        # Touch retrieved items
        for item in selected:
            item.record.touch(now)

        return selected

    def get_memory_context(
        self,
        query_text: str,
        session_id: Optional[str] = None,
        limit: int = 5,
        tiers: Optional[List[MemoryTier]] = None,
    ) -> str:
        """Construct a formatted grounding block of retrieved cognitive memories for prompt insertion."""
        q = MemoryQuery(
            query_text=query_text,
            session_id=session_id,
            limit=limit,
            tiers=tiers,
        )
        retrieved = self.retrieve(q)
        if not retrieved:
            return ""

        lines = ["--- BEGIN COGNITIVE MEMORY CONTEXT (MAG) ---"]
        for item in retrieved:
            lines.append(f"- ({item.record.tier.value.upper()}) {item.record.content}")
        lines.append("--- END COGNITIVE MEMORY CONTEXT ---")
        return "\n".join(lines)

    def consolidate_session_to_semantic(
        self,
        session_id: str,
        min_importance: float = 0.7,
    ) -> int:
        """Consolidate high-value episodic/working memories from a completed session into long-term SEMANTIC memory."""
        mem_ids = self._session_index.get(session_id, set()).copy()
        consolidated_count = 0

        for mid in mem_ids:
            record = self._records.get(mid)
            if not record:
                continue
            if record.importance >= min_importance and record.tier != MemoryTier.SEMANTIC:
                # Promote to semantic memory
                self.remember(
                    content=record.content,
                    tier=MemoryTier.SEMANTIC,
                    importance=record.importance,
                    tags=record.tags + ["consolidated", f"from_session_{session_id}"],
                    metadata={"original_tier": record.tier.value, "source_session": session_id},
                )
                consolidated_count += 1

        logger.info("MAG consolidated %d records from session %s into Semantic memory", consolidated_count, session_id)
        return consolidated_count

    def clear_working_memory(self, session_id: Optional[str] = None) -> int:
        """Clear ephemeral working memories (optionally restricted to a session)."""
        working_ids = self._tier_index.get(MemoryTier.WORKING, set()).copy()
        cleared = 0

        for mid in working_ids:
            record = self._records.get(mid)
            if not record:
                continue
            if session_id is None or record.session_id == session_id:
                self._remove_record(mid)
                cleared += 1

        return cleared

    def prune_decayed_memories(self, min_retention_score: float = 0.01) -> int:
        """Prune memories whose temporal decay and importance have dropped below the retention floor."""
        now = self._time()
        pruned = 0
        all_ids = list(self._records.keys())

        for mid in all_ids:
            rec = self._records[mid]
            # Semantic memories with high importance are never pruned
            if rec.tier == MemoryTier.SEMANTIC and rec.importance >= 0.7:
                continue

            decay = rec.compute_decay_factor(current_time=now, half_life_hours=self.default_half_life_hours)
            effective_weight = rec.importance * decay
            if effective_weight < min_retention_score:
                self._remove_record(mid)
                pruned += 1

        if pruned > 0:
            logger.info("MAG pruned %d decayed memories below score %.3f", pruned, min_retention_score)
        return pruned

    def _tokenize(self, text: str) -> List[str]:
        """Simple, fast tokenization for memory matching."""
        return [w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]{2,}\b", text)]

    def _calculate_relevance(self, query_tokens: List[str], record: MemoryRecord) -> float:
        """Compute relevance score between query tokens and memory record."""
        if not query_tokens:
            return 0.5  # Neutral relevance if query is broad

        record_tokens = set(self._tokenize(record.content))
        tag_tokens = set(t.lower() for t in record.tags)

        # Matched tokens in content
        content_matches = sum(1 for t in query_tokens if t in record_tokens)
        tag_matches = sum(1 for t in query_tokens if t in tag_tokens)

        total_query_terms = len(set(query_tokens))
        if total_query_terms == 0:
            return 0.0

        overlap_ratio = content_matches / total_query_terms
        tag_bonus = min(0.3, tag_matches * 0.15)

        return min(1.0, overlap_ratio + tag_bonus)

    def _remove_record(self, memory_id: str) -> None:
        """Internal helper to remove memory record and clear index pointers."""
        record = self._records.pop(memory_id, None)
        if not record:
            return

        self._tier_index[record.tier].discard(memory_id)
        if record.session_id and record.session_id in self._session_index:
            self._session_index[record.session_id].discard(memory_id)
            if not self._session_index[record.session_id]:
                del self._session_index[record.session_id]

    def __len__(self) -> int:
        return len(self._records)

    def __bool__(self) -> bool:
        return True
