"""
Xeren Core Experience Subsystem — Causal Engine & Memory Store
==============================================================
Provides structured causal learning across:
  (Action -> Result -> RootCause -> NewStrategy)

Features:
- Anti-Poison Quarantine Buffer with PII/secret scrubbing
- SQLite WAL persistent store with FTS5 sub-millisecond retrieval
- Pre-execution causal advisory for agents and MoS specialists
- Continuous training dataset export for Specialist M12
"""

from .distiller import CausalDistiller
from .engine import ExperienceStoreCausalEngine
from .models import (
    CausalAdvisory,
    CausalRecommendation,
    CausalTuple,
    CausalWarning,
    ReviewStatus,
)
from .quarantine_gate import AntiPoisonQuarantineGate
from .store import CausalExperienceStore

__all__ = [
    "CausalAdvisory",
    "CausalDistiller",
    "CausalExperienceStore",
    "CausalRecommendation",
    "CausalTuple",
    "CausalWarning",
    "ExperienceStoreCausalEngine",
    "AntiPoisonQuarantineGate",
    "ReviewStatus",
]
