"""Task state, status, and observation models for autonomous task execution."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid

from pydantic import BaseModel, Field

from xeren.agent.actions import Action, ActionResult


class TaskStatus(str, Enum):
    """Lifecycle statuses of an autonomous agent task."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class Observation(BaseModel):
    """Structured perception/observation post-action execution."""

    observation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this observation",
    )
    action_id: str = Field(
        ...,
        description="Identifier of the action that led to this observation",
    )
    success: bool = Field(
        ...,
        description="Whether the observed action succeeded",
    )
    summary: str = Field(
        ...,
        description="Human- or machine-interpretable summary of the observed outcome",
    )
    data: Optional[Any] = Field(
        default=None,
        description="Structured observation data or payload",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error detail if execution failed",
    )
    artifacts_discovered: Dict[str, Any] = Field(
        default_factory=dict,
        description="Artifacts captured or produced during this observation",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the observation was recorded",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry and contextual metadata",
    )

    model_config = {"arbitrary_types_allowed": True}


class TaskState(BaseModel):
    """Comprehensive runtime state for an autonomous task."""

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the task execution",
    )
    goal: str = Field(
        ...,
        description="User-defined goal or prompt for the autonomous agent",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current lifecycle status of the task",
    )
    current_step: Optional[Action] = Field(
        default=None,
        description="The action currently being considered or executed",
    )
    completed_steps: List[Any] = Field(
        default_factory=list,
        description="Chronological record of successfully executed actions",
    )
    failed_steps: List[Any] = Field(
        default_factory=list,
        description="Chronological record of failed action attempts",
    )
    remaining_steps: List[Any] = Field(
        default_factory=list,
        description="Pending sequence of planned actions awaiting execution",
    )
    observations: List[Observation] = Field(
        default_factory=list,
        description="Perceptual observations collected across all steps",
    )
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Artifacts accumulated during execution (files, dataframes, urls, reports)",
    )
    attempt_count: int = Field(
        default=0,
        ge=0,
        description="Total execution cycles/steps attempted for this task",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual, configuration, and diagnostic metadata",
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_terminal(self) -> bool:
        """Return True if the task has reached a terminal state."""
        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        }

    @property
    def memory(self) -> Dict[str, Any]:
        """Backward-compatibility alias for metadata/context."""
        return self.metadata

    @property
    def step_count(self) -> int:
        """Backward-compatibility alias for attempt_count."""
        return self.attempt_count

    @property
    def session_id(self) -> str:
        """Backward-compatibility alias for task_id."""
        return self.task_id

    @property
    def task(self) -> str:
        """Backward-compatibility alias for goal."""
        return self.goal

    @property
    def plan(self) -> List[Any]:
        """Backward-compatibility alias for remaining_steps."""
        return self.remaining_steps

    @property
    def history(self) -> List[Tuple[Any, ActionResult]]:
        """Backward-compatibility alias returning history tuples of (action, result)."""
        return [(getattr(r, "action", r), r) for r in self.completed_steps]

    def record_observation(self, obs: Observation) -> None:
        """Append an observation and merge any newly discovered artifacts."""
        self.observations.append(obs)
        if obs.artifacts_discovered:
            self.artifacts.update(obs.artifacts_discovered)

    def record_success(self, action: Action, result: ActionResult) -> None:
        """Update state when an action completes successfully."""
        self.completed_steps.append(result)
        if result.artifacts:
            self.artifacts.update(result.artifacts)
        if self.remaining_steps and self.remaining_steps[0].action_id == action.action_id:
            self.remaining_steps.pop(0)
        self.current_step = None

    def record_failure(self, action: Action, result: ActionResult) -> None:
        """Update state when an action execution fails."""
        self.failed_steps.append(result)

    def add_artifact(self, name: str, artifact: Any) -> None:
        """Register an artifact into the task state."""
        self.artifacts[name] = artifact


__all__ = [
    "TaskStatus",
    "Observation",
    "TaskState",
]
