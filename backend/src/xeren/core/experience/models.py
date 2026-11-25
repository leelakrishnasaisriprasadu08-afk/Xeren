"""
Xeren ExperienceStore Causal Engine — Domain Models & Schemas
============================================================
Defines the authoritative CausalTuple schema:
  (task_id, objective, action, result, root_cause, new_strategy, status, timestamp)

Adheres strictly to the Xeren 5-Phase Blueprint specifications:
- Anti-poison quarantine review state machine
- Pre-execution advisory warnings and recommendations
- SHA-256 deterministic cryptographic fingerprinting
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional


class ReviewStatus(str, Enum):
    """Lifecycle review status for anti-poison quarantine gate."""
    UNREVIEWED = "UNREVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


@dataclass
class CausalTuple:
    """Core causal lesson unit capturing an operational action, outcome, and distillation."""

    task_id: str
    objective: str
    action: str
    result: str
    success: bool
    root_cause: Optional[str] = None
    new_strategy: Optional[str] = None
    verification_score: float = 1.0
    status: ReviewStatus = ReviewStatus.UNREVIEWED
    fingerprint: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = ReviewStatus(self.status)
        if not self.fingerprint:
            self.fingerprint = self.compute_fingerprint()

    def compute_fingerprint(self) -> str:
        """Deterministic SHA-256 fingerprint over core causal tuple components."""
        clean_obj = self.objective.strip().lower()
        clean_act = self.action.strip().lower()
        clean_res = self.result.strip().lower()[:500]
        clean_cause = (self.root_cause or "").strip().lower()
        clean_strat = (self.new_strategy or "").strip().lower()

        payload = f"{clean_obj}|{clean_act}|{clean_res}|{clean_cause}|{clean_strat}|{self.success}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CausalTuple:
        data_copy = dict(data)
        if "status" in data_copy and isinstance(data_copy["status"], str):
            data_copy["status"] = ReviewStatus(data_copy["status"])
        return cls(**data_copy)


@dataclass
class CausalWarning:
    """Specific warning derived from past similar failures to avoid repeated mistakes."""

    past_action: str
    failure_reason: str
    root_cause: str
    avoidance_advice: str
    severity: str = "medium"  # "low", "medium", "high", "critical"
    fingerprint: str = ""


@dataclass
class CausalRecommendation:
    """Positive recommendation derived from verified historical success."""

    past_action: str
    proven_strategy: str
    confidence: float = 1.0
    fingerprint: str = ""


@dataclass
class CausalAdvisory:
    """Pre-execution advisory informing the agent/orchestrator of past causal patterns."""

    objective: str
    proposed_action: str
    should_proceed: bool
    confidence: float
    warnings: List[CausalWarning] = field(default_factory=list)
    recommendations: List[CausalRecommendation] = field(default_factory=list)
    suggested_strategy: Optional[str] = None
