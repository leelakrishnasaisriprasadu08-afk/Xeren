"""
Xeren MoS — Inter-Model Message Protocol
==========================================
Strict JSON-serializable schemas for all messages passed between:
  - Main Model → ToolCaller (DispatchRequest)
  - ToolCaller  → Specialist (SpecialistTask)
  - Specialist  → ToolCaller (SpecialistResult)
  - ToolCaller  → Main Model (AggregatedResponse)

Every message carries a trace_id for end-to-end observability.
"""
from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Status codes
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    SUCCESS    = "success"
    FAILED     = "failed"
    SKIPPED    = "skipped"
    CANCELLED  = "cancelled"


class RiskLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# ---------------------------------------------------------------------------
# Base message
# ---------------------------------------------------------------------------

@dataclass
class MoSMessage:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        import dataclasses, json
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# 1. Main Model → ToolCaller
# ---------------------------------------------------------------------------

@dataclass
class DispatchRequest(MoSMessage):
    """
    The main model sends this to ToolCaller when it determines
    that specialist help is needed.
    """
    user_query: str = ""                    # original user text
    task_description: str = ""             # main model's interpretation
    required_capabilities: List[str] = field(default_factory=list)
    # e.g. ["reasoning", "coding"] — ToolCaller selects specialists from these

    context: Dict[str, Any] = field(default_factory=dict)
    # any retrieved context (RAG/CAG/MAG results, memory, etc.)

    allow_parallel: bool = True            # can specialists run in parallel?
    max_specialists: int = 3              # cap to avoid runaway chaining
    risk_level: RiskLevel = RiskLevel.LOW
    requires_permission: bool = False


# ---------------------------------------------------------------------------
# 2. ToolCaller → Specialist
# ---------------------------------------------------------------------------

@dataclass
class SpecialistTask(MoSMessage):
    """
    ToolCaller sends this to one specialist model.
    Each specialist gets a focused sub-task derived from the DispatchRequest.
    """
    dispatch_trace_id: str = ""            # links back to original DispatchRequest
    specialist_id: str = ""               # e.g. "M2_reasoning"
    specialist_name: str = ""             # human-readable e.g. "M2 — Reasoning"

    sub_task: str = ""                    # focused task description for THIS specialist
    input_data: Dict[str, Any] = field(default_factory=dict)
    # structured input (e.g. code snippet for M7, dataset for M5, etc.)

    expected_output_format: str = "text"  # "text" | "json" | "code" | "plan"
    max_tokens: int = 2048
    timeout_seconds: float = 60.0


# ---------------------------------------------------------------------------
# 3. Specialist → ToolCaller
# ---------------------------------------------------------------------------

@dataclass
class SpecialistResult(MoSMessage):
    """
    A specialist model's output, returned to ToolCaller.
    """
    task_trace_id: str = ""              # links back to SpecialistTask
    specialist_id: str = ""
    status: TaskStatus = TaskStatus.SUCCESS

    output: str = ""                     # primary text output
    structured_output: Dict[str, Any] = field(default_factory=dict)
    # machine-readable output when format="json" or "code"

    confidence: float = 1.0             # [0.0, 1.0] — specialist's self-assessment
    error: Optional[str] = None
    execution_ms: float = 0.0


# ---------------------------------------------------------------------------
# 4. ToolCaller → Main Model  (aggregated)
# ---------------------------------------------------------------------------

@dataclass
class AggregatedResponse(MoSMessage):
    """
    ToolCaller combines all specialist results and returns this
    to the Main model for final synthesis and user response.
    """
    dispatch_trace_id: str = ""
    status: TaskStatus = TaskStatus.SUCCESS

    specialist_results: List[SpecialistResult] = field(default_factory=list)
    synthesis: str = ""                   # ToolCaller's combined summary
    recommended_response: str = ""        # suggested final answer for Main to refine

    total_specialists_used: int = 0
    total_execution_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
