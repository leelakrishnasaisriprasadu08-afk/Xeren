"""
Xeren MoS — Specialist Registry
================================
Defines the 13 specialist model identities (M1–M12 + ToolCaller).
Each specialist has:
  - A unique ID and human name
  - A list of capability domains it handles
  - The model checkpoint path it loads from
  - Priority weight for task routing

The MoSOrchestrator uses this registry to decide which specialist(s)
to call for a given task.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Specialist IDs
# ---------------------------------------------------------------------------

class SpecialistID(str, Enum):
    TOOL_CALLER   = "tool_caller"
    UNDERSTANDING = "M1_understanding"
    REASONING     = "M2_reasoning"
    KNOWLEDGE     = "M3_knowledge"
    RESEARCH      = "M4_research"
    ANALYSIS      = "M5_analysis"
    PLANNING      = "M6_planning"
    CODING        = "M7_coding"
    SIMULATION    = "M8_simulation"
    CRITIC        = "M9_critic"
    VERIFICATION  = "M10_verification"
    OPTIMIZATION  = "M11_optimization"
    EXPERIENCE    = "M12_experience"


# ---------------------------------------------------------------------------
# Specialist definition
# ---------------------------------------------------------------------------

@dataclass
class SpecialistSpec:
    """Complete definition of one specialist model."""
    id: SpecialistID
    name: str
    description: str
    capabilities: List[str]          # domain keywords for routing
    checkpoint_dir: str              # relative path inside project
    param_budget: str = "500M"        # target parameter size (< 1B)
    priority: int = 5                # 1 (highest) → 10 (lowest)
    enabled: bool = True
    loaded: bool = False             # set True at runtime when weights are loaded
    extra: dict = field(default_factory=dict)

    @property
    def checkpoint_path(self) -> Path:
        return Path(self.checkpoint_dir)

    def matches(self, capability: str) -> bool:
        cap_clean = capability.lower().strip()
        stem = cap_clean[:-3] if cap_clean.endswith("ing") else cap_clean
        for c in self.capabilities:
            if c in cap_clean or cap_clean in c:
                return True
            if stem and (stem in c or c.startswith(stem) or (len(stem) >= 3 and c.startswith(stem[:3]))):
                return True
            if len(c) >= 4 and len(cap_clean) >= 4 and cap_clean[:4] == c[:4]:
                return True
        return False


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class SpecialistRegistry:
    """Singleton that holds all specialist specs. Thread-safe for reads."""

    _SPECS: List[SpecialistSpec] = [
        SpecialistSpec(
            id=SpecialistID.TOOL_CALLER,
            name="ToolCaller",
            description="Lightweight router: interprets Main model dispatch signals, "
                        "selects specialist(s), formats inter-model messages.",
            capabilities=["dispatch", "route", "call", "tool", "function", "delegate"],
            checkpoint_dir="training/checkpoints/mos/tool_caller",
            param_budget="200M",
            priority=1,
        ),
        SpecialistSpec(
            id=SpecialistID.UNDERSTANDING,
            name="M1 — Understanding",
            description="Parses the situation, extracts intent, entities, and context.",
            capabilities=["understand", "parse", "intent", "context", "what does", "clarify"],
            checkpoint_dir="training/checkpoints/mos/m1_understanding",
            param_budget="400M",
            priority=2,
        ),
        SpecialistSpec(
            id=SpecialistID.REASONING,
            name="M2 — Reasoning",
            description="Solves complex logical, causal, and multi-step reasoning tasks.",
            capabilities=["reason", "reasoning", "logic", "why", "cause", "deduce", "infer", "if-then", "math"],
            checkpoint_dir="training/checkpoints/mos/m2_reasoning",
            param_budget="800M",
            priority=3,
        ),
        SpecialistSpec(
            id=SpecialistID.KNOWLEDGE,
            name="M3 — Knowledge",
            description="Connects concepts and applies learned factual knowledge.",
            capabilities=["know", "knowledge", "fact", "define", "explain", "what is", "tell me about"],
            checkpoint_dir="training/checkpoints/mos/m3_knowledge",
            param_budget="600M",
            priority=4,
        ),
        SpecialistSpec(
            id=SpecialistID.RESEARCH,
            name="M4 — Research",
            description="Finds, retrieves, and synthesizes new information from sources.",
            capabilities=["research", "researching", "find", "search", "latest", "news", "source", "web"],
            checkpoint_dir="training/checkpoints/mos/m4_research",
            param_budget="700M",
            priority=4,
        ),
        SpecialistSpec(
            id=SpecialistID.ANALYSIS,
            name="M5 — Analysis",
            description="Breaks complex information into patterns and insights.",
            capabilities=["analysis", "analyze", "analyzing", "pattern", "data", "compare", "statistics", "breakdown"],
            checkpoint_dir="training/checkpoints/mos/m5_analysis",
            param_budget="500M",
            priority=4,
        ),
        SpecialistSpec(
            id=SpecialistID.PLANNING,
            name="M6 — Planning",
            description="Determines possible strategies and action sequences.",
            capabilities=["plan", "planning", "strategy", "steps", "roadmap", "schedule", "how to", "workflow"],
            checkpoint_dir="training/checkpoints/mos/m6_planning",
            param_budget="600M",
            priority=3,
        ),
        SpecialistSpec(
            id=SpecialistID.CODING,
            name="M7 — Coding / Creation",
            description="Produces technical code and creative solutions.",
            capabilities=["code", "coding", "program", "programming", "build", "create", "implement", "python", "script", "develop"],
            checkpoint_dir="training/checkpoints/mos/m7_coding",
            param_budget="800M",
            priority=3,
        ),
        SpecialistSpec(
            id=SpecialistID.SIMULATION,
            name="M8 — Simulation",
            description="Predicts what could happen before an action is taken.",
            capabilities=["simulate", "predict", "what if", "scenario", "forecast", "what would"],
            checkpoint_dir="training/checkpoints/mos/m8_simulation",
            param_budget="500M",
            priority=5,
        ),
        SpecialistSpec(
            id=SpecialistID.CRITIC,
            name="M9 — Critic",
            description="Attempts to find weaknesses, errors, and failure modes.",
            capabilities=["critique", "weakness", "flaw", "error", "review", "problem", "wrong", "risk"],
            checkpoint_dir="training/checkpoints/mos/m9_critic",
            param_budget="500M",
            priority=5,
        ),
        SpecialistSpec(
            id=SpecialistID.VERIFICATION,
            name="M10 — Verification",
            description="Tests whether a result is actually valid and correct.",
            capabilities=["verify", "validate", "check", "test", "correct", "accurate", "true"],
            checkpoint_dir="training/checkpoints/mos/m10_verification",
            param_budget="500M",
            priority=5,
        ),
        SpecialistSpec(
            id=SpecialistID.OPTIMIZATION,
            name="M11 — Optimization",
            description="Improves solutions for speed, quality, or efficiency.",
            capabilities=["optimize", "improve", "faster", "better", "refine", "enhance", "efficiency"],
            checkpoint_dir="training/checkpoints/mos/m11_optimization",
            param_budget="500M",
            priority=6,
        ),
        SpecialistSpec(
            id=SpecialistID.EXPERIENCE,
            name="M12 — Experience / Learning",
            description="Learns useful patterns from past outcomes for continuous improvement.",
            capabilities=["learn", "remember", "history", "past", "experience", "adapt", "feedback"],
            checkpoint_dir="training/checkpoints/mos/m12_experience",
            param_budget="400M",
            priority=7,
        ),
    ]

    _by_id: dict[SpecialistID, SpecialistSpec] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @classmethod
    def _build_index(cls) -> None:
        if not cls._by_id:
            cls._by_id = {s.id: s for s in cls._SPECS}

    @classmethod
    def get(cls, specialist_id: SpecialistID) -> SpecialistSpec:
        cls._build_index()
        return cls._by_id[specialist_id]

    @classmethod
    def all(cls) -> List[SpecialistSpec]:
        return list(cls._SPECS)

    @classmethod
    def enabled(cls) -> List[SpecialistSpec]:
        return [s for s in cls._SPECS if s.enabled]

    @classmethod
    def find_by_capability(cls, capability: str) -> List[SpecialistSpec]:
        """Return specialists (sorted by priority) that match a capability keyword."""
        matches = [s for s in cls._SPECS if s.enabled and s.matches(capability)]
        return sorted(matches, key=lambda s: s.priority)

    @classmethod
    def tool_caller(cls) -> SpecialistSpec:
        cls._build_index()
        return cls._by_id[SpecialistID.TOOL_CALLER]

    def __repr__(self) -> str:
        return f"SpecialistRegistry({len(self._SPECS)} specialists)"
