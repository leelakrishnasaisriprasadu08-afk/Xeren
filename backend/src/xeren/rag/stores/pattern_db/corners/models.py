"""
Xeren Sovereign Pattern DB — Multi-Corner Pattern Models
=========================================================
Implements the 9 Pattern Corners:
- WORKFLOW: DAG definitions, steps, graph expansion
- EXECUTION_TRACE: Run logs, step timings, columnar filtering
- TOOL_SCHEMA: Registry, params, types, exact/BM25 lookups
- INTENT_SOLUTION: Case table mapping user intent -> winning solution
- FAILURE_FIX: Error signature -> tested resolution (BM25 first, vector second)
- RULES_PERMISSIONS: Security policies, CAG pre-load, zero vectors
- ENTITY_STATE: Users, files, resource state, pure relational/KV
- VOLATILE_WEB: Live data with TTL & freshness filters
- EPISODIC_MEMORY: Per-agent time-ordered trajectory memory

Three-Form Record Representation:
1. RAW: Original JSON/log for exactness
2. SIGNATURE: Normalized steps with parameters stripped & hashed
3. SUMMARY_TEXT: Plain-language doc2query questions for dense embedding
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import time
from typing import Any, Dict, List, Optional


class PatternCorner(str, Enum):
    """The 9 specialized pattern corners for automation & RAG."""

    WORKFLOW = "workflow"
    EXECUTION_TRACE = "execution_trace"
    TOOL_SCHEMA = "tool_schema"
    INTENT_SOLUTION = "intent_solution"
    FAILURE_FIX = "failure_fix"
    RULES_PERMISSIONS = "rules_permissions"
    ENTITY_STATE = "entity_state"
    VOLATILE_WEB = "volatile_web"
    EPISODIC_MEMORY = "episodic_memory"


@dataclass
class ThreeFormRecord:
    """Stores each pattern in Raw, Signature, and Summary/doc2query forms."""

    pattern_id: str
    corner: PatternCorner
    raw: Dict[str, Any]
    signature: str
    summary_text: str
    doc2query_questions: List[str] = field(default_factory=list)
    vector: Optional[List[float]] = None
    success_count: int = 1
    failure_count: int = 0
    created_at: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None
    agent_id: Optional[str] = None
    parent_workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def trust_score(self) -> float:
        """Calculate empirical success ratio."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def is_expired(self) -> bool:
        """Check if record has exceeded TTL."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["corner"] = self.corner.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ThreeFormRecord:
        data_copy = dict(data)
        if isinstance(data_copy.get("corner"), str):
            data_copy["corner"] = PatternCorner(data_copy["corner"])
        return cls(**data_copy)


@dataclass
class CornerQueryResult:
    """Ranked match returned from a specific pattern corner."""

    record: ThreeFormRecord
    corner: PatternCorner
    score: float
    retrieval_method: str  # "exact", "bm25", "vector", "hybrid", "recency"
    matched_signature: bool = False
    parent_workflow: Optional[Dict[str, Any]] = None
