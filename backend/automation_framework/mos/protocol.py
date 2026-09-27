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
class AssignmentExpectation:
    """Expectation schema used by Output Verifier to validate specialist deliverables."""
    format: str = "text"                  # "text" | "json" | "code" | "plan"
    required_keys: List[str] = field(default_factory=list)
    non_empty: bool = True
    syntax_check: bool = True
    max_latency_ms: float = 60000.0


@dataclass
class TaskAssignment:
    """A single specialist task assignment produced by the Work Assigner."""
    specialist_id: str
    action: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    expectation: AssignmentExpectation = field(default_factory=AssignmentExpectation)
    confidence: float = 1.0               # [0.0 - 1.0] confidence score
    priority: int = 1


@dataclass
class WorkAssignmentPlan(MoSMessage):
    """
    Structured outcome of the Work Assigner phase.
    Zero natural language commentary — pure actionable dispatch matrix.
    """
    is_executable: bool = True
    confidence: float = 1.0               # [0.0 - 1.0]
    execution_strategy: str = "sequential"# "sequential" | "parallel"
    assignments: List[TaskAssignment] = field(default_factory=list)
    reason_code: str = "DIRECT_MATCH"


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
    expectation: AssignmentExpectation = field(default_factory=AssignmentExpectation)
    max_tokens: int = 2048
    timeout_seconds: float = 60.0


# ---------------------------------------------------------------------------
# 3. Output Verifier Verdict & Specialist Result
# ---------------------------------------------------------------------------

@dataclass
class VerificationVerdict(MoSMessage):
    """
    Structured outcome of the Output Verifier phase.
    Ultra-fast discriminator response: pure booleans, metrics, and error triage.
    """
    task_trace_id: str = ""
    specialist_id: str = ""
    passed: bool = True
    expectations_met: bool = True
    confidence: float = 1.0               # [0.0 - 1.0] verification accuracy
    has_error: bool = False
    syntax_valid: bool = True
    needs_retry: bool = False
    error_type: Optional[str] = None
    score: float = 1.0                    # [0.0 - 1.0] quality score
    retry_adjustments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpecialistResult(MoSMessage):
    """
    A specialist model's output, returned to ToolCaller and verified.
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
    verification: Optional[VerificationVerdict] = None


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
    all_passed: bool = True
    overall_confidence: float = 1.0

    specialist_results: List[SpecialistResult] = field(default_factory=list)
    verification_verdicts: List[VerificationVerdict] = field(default_factory=list)
    synthesis: str = ""                   # ToolCaller's combined summary
    recommended_response: str = ""        # suggested final answer for Main to refine

    total_specialists_used: int = 0
    total_execution_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
