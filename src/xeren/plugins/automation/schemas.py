"""Pydantic schemas and typed data models for Xeren Automation / Task Plugin."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field, model_validator


class AutomationOperation(str, Enum):
    """The 10 core operations supported by AutomationPlugin."""

    TASK_CREATE = "task_create"
    TASK_PLAN = "task_plan"
    TASK_EXECUTE = "task_execute"
    TASK_PAUSE = "task_pause"
    TASK_RESUME = "task_resume"
    TASK_CANCEL = "task_cancel"
    TASK_STATUS = "task_status"
    TASK_RETRY = "task_retry"
    TASK_DEPENDENCY_MANAGEMENT = "task_dependency_management"
    TASK_HISTORY = "task_history"


class TaskStatus(str, Enum):
    """Lifecycle statuses for high-level tasks."""

    PENDING = "pending"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Lifecycle statuses for individual task steps."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class RetryPolicy(BaseModel):
    """Configuration governing step retry behavior."""

    max_retries: int = Field(default=2, ge=0, le=10, description="Maximum number of retry attempts")
    initial_interval_seconds: float = Field(default=1.0, ge=0.0, description="Initial backoff delay in seconds")
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Exponential backoff multiplier")
    max_interval_seconds: float = Field(default=30.0, ge=0.0, description="Maximum backoff ceiling in seconds")
    non_retryable_errors: List[str] = Field(
        default_factory=list, description="Keywords or error patterns that should not be retried"
    )
    retryable_errors: List[str] = Field(
        default_factory=list, description="Keywords or error patterns that should be retried"
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_retry(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "backoff_seconds" in data and "initial_interval_seconds" not in data:
                data["initial_interval_seconds"] = data["backoff_seconds"]
            if "backoff_multiplier" in data and "backoff_factor" not in data:
                data["backoff_factor"] = data["backoff_multiplier"]
        return data

    @property
    def backoff_seconds(self) -> float:
        return self.initial_interval_seconds

    @property
    def backoff_multiplier(self) -> float:
        return self.backoff_factor


class TaskStep(BaseModel):
    """Atomic step within a multi-step orchestrated task."""

    id: str = Field(
        default_factory=lambda: f"step_{str(uuid.uuid4())[:8]}",
        description="Unique identifier for the step",
    )
    title: str = Field(default="", description="Human-readable title or label for the step")
    plugin_name: str = Field(..., description="Target plugin to execute (e.g. 'research', 'data', 'coding')")
    operation: str = Field(default="", description="Specific plugin operation or capability to invoke")
    action: Optional[str] = Field(default=None, description="Action alias for operation")
    input_data: Dict[str, Any] = Field(
        default_factory=dict, description="Input payload passed to the target plugin"
    )
    input_payload: Optional[Dict[str, Any]] = Field(
        default=None, description="Input payload alias"
    )
    depends_on: List[str] = Field(
        default_factory=list, description="List of step IDs that must complete before this step"
    )
    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy, description="Retry configuration for this step"
    )
    retry_count: int = Field(default=0, ge=0, description="Number of times this step has been retried")
    timeout_seconds: Optional[float] = Field(
        default=60.0, gt=0.0, description="Maximum execution time allowed for this step"
    )
    is_optional: bool = Field(
        default=False, description="If True, step failure does not fail the overall task"
    )
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current execution status of step")
    output: Optional[Any] = Field(default=None, description="Output returned by successful plugin execution")
    error: Optional[str] = Field(default=None, description="Diagnostic error if step failed")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds")
    started_at: Optional[datetime] = Field(default=None, description="Timestamp execution started")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp execution finished")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary step metadata")

    @model_validator(mode="before")
    @classmethod
    def _normalize_step(cls, data: Any) -> Any:
        if isinstance(data, dict):
            step_id = data.get("id") or f"step_{str(uuid.uuid4())[:8]}"
            data["id"] = step_id
            if not data.get("title"):
                data["title"] = step_id
            op = data.get("operation") or data.get("action") or "execute"
            data["operation"] = op
            data["action"] = op
            if "input_payload" in data and "input_data" not in data:
                data["input_data"] = data["input_payload"]
            elif "input_data" in data and "input_payload" not in data:
                data["input_payload"] = data["input_data"]
        return data


class TaskPlan(BaseModel):
    """Structured execution graph and DAG definition for a multi-step task."""

    task_id: str = Field(
        default_factory=lambda: f"task_{str(uuid.uuid4())[:8]}",
        description="Unique identifier for the task plan",
    )
    objective: str = Field(..., description="Overall goal or user instruction for the task")
    steps: List[TaskStep] = Field(default_factory=list, description="Ordered steps in the execution DAG")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current state of the entire task")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC last updated timestamp"
    )
    timeout_seconds: Optional[float] = Field(
        default=300.0, gt=0.0, description="Total timeout allowed for task execution"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom task metadata")


class StepRunRecord(BaseModel):
    """Historical record of an individual step execution run/attempt."""

    step_id: str = Field(..., description="ID of the executed step")
    run_index: int = Field(default=1, ge=1, description="Run attempt index (1 for initial run, 2+ for retries)")
    attempt: Optional[int] = Field(default=None, description="Run attempt alias")
    status: StepStatus = Field(default=StepStatus.COMPLETED, description="Final status of this run attempt")
    success: Optional[bool] = Field(default=None, description="Success flag alias")
    output: Optional[Any] = Field(default=None, description="Output payload if run succeeded")
    error: Optional[str] = Field(default=None, description="Error message if run failed")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Run start timestamp"
    )
    completed_at: Optional[datetime] = Field(default=None, description="Run completion timestamp")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Run latency in milliseconds")

    @model_validator(mode="before")
    @classmethod
    def _normalize_record(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "attempt" in data and "run_index" not in data and data["attempt"] is not None:
                data["run_index"] = data["attempt"]
            if "success" in data and "status" not in data and data["success"] is not None:
                data["status"] = StepStatus.COMPLETED if data["success"] else StepStatus.FAILED
        return data


class TaskHistoryEntry(BaseModel):
    """Chronological audit log event for task state transitions and step actions."""

    task_id: str = Field(..., description="Target task ID")
    event_type: str = Field(..., description="Name of the event (e.g. 'step_started', 'task_paused')")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Event UTC timestamp"
    )
    step_id: Optional[str] = Field(default=None, description="Associated step ID if step-specific")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic or state details")


class AutomationInput(BaseModel):
    """Input payload for Automation Plugin operations."""

    operation: AutomationOperation = Field(
        default=AutomationOperation.TASK_EXECUTE,
        description="The automation operation to perform",
    )
    task_id: Optional[str] = Field(default=None, description="Target task ID for status, cancel, resume, etc.")
    objective: Optional[str] = Field(default=None, description="Objective or instruction to plan and execute")
    steps: Optional[List[TaskStep]] = Field(default=None, description="Explicit steps list for task creation")
    plan: Optional[TaskPlan] = Field(default=None, description="Pre-composed task plan to execute")
    step_id: Optional[str] = Field(default=None, description="Specific step ID for targeted retry or inspection")
    auto_plan: bool = Field(default=True, description="Whether to auto-generate plan if steps are empty")
    max_steps: Optional[int] = Field(default=50, ge=1, le=200, description="Safety limit on maximum steps in a task")
    timeout_seconds: Optional[float] = Field(default=300.0, gt=0.0, description="Execution timeout in seconds")
    limit: int = Field(default=50, ge=1, description="Maximum history items or list entries to retrieve")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or configuration")


class AutomationResult(BaseModel):
    """Result payload produced by Automation Plugin operations."""

    operation: AutomationOperation = Field(..., description="The operation that was executed")
    success: bool = Field(default=True, description="Whether the operation succeeded")
    task_id: Optional[str] = Field(default=None, description="Associated task ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current overall task status")
    plan: Optional[TaskPlan] = Field(default=None, description="Active task plan with step states and outputs")
    step_results: Dict[str, Any] = Field(
        default_factory=dict, description="Mapping of step_id to step output payload"
    )
    history: List[TaskHistoryEntry] = Field(
        default_factory=list, description="Chronological audit history of the task"
    )
    error: Optional[str] = Field(default=None, description="Diagnostic error message if operation failed")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Total execution latency in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics and metadata")

    @property
    def completed_steps(self) -> List[str]:
        """List of step IDs that completed successfully."""
        if not self.plan:
            return []
        return [s.id for s in self.plan.steps if s.status == StepStatus.COMPLETED]

    @property
    def failed_steps(self) -> List[str]:
        """List of step IDs that failed."""
        if not self.plan:
            return []
        return [s.id for s in self.plan.steps if s.status == StepStatus.FAILED]

    @property
    def step_errors(self) -> Dict[str, str]:
        """Mapping of failed step IDs to error diagnostic messages."""
        if not self.plan:
            return {}
        return {s.id: s.error for s in self.plan.steps if s.status == StepStatus.FAILED and s.error}

    @property
    def retry_attempts(self) -> Dict[str, int]:
        """Mapping of step IDs to count of retries performed."""
        if not self.plan:
            return {}
        return {s.id: s.retry_count for s in self.plan.steps if s.retry_count > 0}

    @property
    def step_details(self) -> List[Dict[str, Any]]:
        """Structured execution metadata for all steps in the plan."""
        if not self.plan:
            return []
        return [
            {
                "step_id": s.id,
                "title": s.title,
                "plugin_name": s.plugin_name,
                "operation": s.operation,
                "status": s.status.value,
                "retry_count": s.retry_count,
                "latency_ms": s.latency_ms,
                "error": s.error,
            }
            for s in self.plan.steps
        ]

    @property
    def final_outcome(self) -> Dict[str, Any]:
        """Structured summary of the final execution outcome."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "success": self.success,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "step_errors": self.step_errors,
            "retry_attempts": self.retry_attempts,
            "step_results": self.step_results,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }

    def to_experience_payload(self) -> Dict[str, Any]:
        """
        Export a structured execution outcome dictionary designed for consumption by
        Verification Plugin (Plugin #7) and Experience Plugin (Plugin #8).
        """
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "success": self.success,
            "objective": self.plan.objective if self.plan else "",
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "errors": self.step_errors,
            "retry_attempts": self.retry_attempts,
            "step_results": self.step_results,
            "step_details": self.step_details,
            "history_count": len(self.history),
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


__all__ = [
    "AutomationOperation",
    "TaskStatus",
    "StepStatus",
    "RetryPolicy",
    "TaskStep",
    "TaskPlan",
    "StepRunRecord",
    "TaskHistoryEntry",
    "AutomationInput",
    "AutomationResult",
]
