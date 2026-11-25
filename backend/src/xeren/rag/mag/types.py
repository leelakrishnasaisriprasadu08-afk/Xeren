"""Data structures and configuration models for Memory-Augmented Generation (MAG)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    """Hierarchical memory tiers for cognitive retrieval."""

    WORKING = "working"      # Active session constraints, scratchpad, current task context
    EPISODIC = "episodic"    # Past interaction history, user corrections, execution outcomes
    SEMANTIC = "semantic"    # Consolidated facts, developer preferences, project conventions


@dataclass
class MemoryRecord:
    """A cognitive unit of memory in the MAG subsystem."""

    memory_id: str
    tier: MemoryTier
    content: str
    importance: float = 0.5  # 0.0 (trivial) to 1.0 (mission critical)
    session_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self, current_time: Optional[float] = None) -> None:
        """Mark memory as retrieved/accessed."""
        now = current_time if current_time is not None else time.time()
        self.last_accessed_at = now
        self.access_count += 1

    def compute_decay_factor(
        self,
        current_time: Optional[float] = None,
        half_life_hours: float = 72.0,
    ) -> float:
        """Calculate exponential recency decay factor e^(-lambda * dt)."""
        now = current_time if current_time is not None else time.time()
        elapsed_hours = max(0.0, (now - self.created_at) / 3600.0)

        # Working memory decays much faster (e.g. half-life of 2 hours)
        if self.tier == MemoryTier.WORKING:
            half_life_hours = min(half_life_hours, 2.0)
        elif self.tier == MemoryTier.SEMANTIC:
            # Semantic memory is persistent (half-life of 720 hours ~ 30 days)
            half_life_hours = max(half_life_hours, 720.0)

        if half_life_hours <= 0:
            return 1.0

        decay_lambda = math.log(2) / half_life_hours
        return math.exp(-decay_lambda * elapsed_hours)


class MemoryQuery(BaseModel):
    """Parameters for querying the cognitive memory engine."""

    query_text: str = Field(..., description="Search query or context to associate")
    tiers: Optional[List[MemoryTier]] = Field(
        default=None, description="Memory tiers to inspect (None checks all)"
    )
    session_id: Optional[str] = Field(
        default=None, description="Optional active session filter for working memory"
    )
    limit: int = Field(default=5, ge=1, le=50, description="Max memory items to return")
    min_score: float = Field(default=0.05, ge=0.0, description="Minimum cognitive score cutoff")
    half_life_hours: float = Field(default=72.0, gt=0.0, description="Recency decay half-life in hours")


@dataclass
class RetrievedMemory:
    """A scored memory item returned from MAG retrieval."""

    record: MemoryRecord
    score: float
    relevance: float
    recency_factor: float
    importance: float

    def format(self) -> str:
        """Format as a grounded memory block."""
        tier_label = self.record.tier.value.upper()
        return f"[{tier_label} MEMORY: score={self.score:.2f}] {self.record.content}"
