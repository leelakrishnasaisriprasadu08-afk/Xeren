"""Data structures and configuration models for Cache-Augmented Generation (CAG)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from xeren.rag.context.types import Citation, GroundedContext


class CachePolicy(str, Enum):
    """Eviction and invalidation policies for the CAG engine."""

    TTL = "ttl"
    LRU = "lru"
    HASH_INVALIDATION = "hash_invalidation"
    ADAPTIVE = "adaptive"


@dataclass
class CachedContextEntry:
    """A single cached context entry in the CAG layer."""

    cache_key: str
    query: str
    context_text: str
    grounded_context: Optional[GroundedContext] = None
    citations: List[Citation] = field(default_factory=list)
    content_hashes: Set[str] = field(default_factory=set)
    source_identifiers: Set[str] = field(default_factory=set)
    tenant_id: Optional[str] = None
    scope: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    estimated_latency_savings_ms: float = 85.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Return True if entry has surpassed its TTL."""
        if self.expires_at is None:
            return False
        now = current_time if current_time is not None else time.time()
        return now >= self.expires_at

    def touch(self, current_time: Optional[float] = None) -> None:
        """Mark entry as accessed."""
        now = current_time if current_time is not None else time.time()
        self.last_accessed_at = now
        self.access_count += 1


class CacheStats(BaseModel):
    """Operational telemetry and hit-rate metrics for CAG."""

    hits: int = Field(default=0, ge=0)
    misses: int = Field(default=0, ge=0)
    evictions: int = Field(default=0, ge=0)
    invalidations: int = Field(default=0, ge=0)
    total_latency_saved_ms: float = Field(default=0.0, ge=0.0)
    total_tokens_saved: int = Field(default=0, ge=0)

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        total = self.total_requests
        if total == 0:
            return 0.0
        return self.hits / total
