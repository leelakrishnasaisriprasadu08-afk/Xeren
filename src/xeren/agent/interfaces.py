"""Core interfaces and abstract protocols for the Xeren Autonomous Work Agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

from xeren.agent.actions import Action, ActionResult, PermissionLevel
from xeren.agent.state import Observation, TaskState
from xeren.plugins.contract import PluginExecutionContext

if TYPE_CHECKING:
    from xeren.agent.planner import TaskPlan


# -------------------------------------------------------------------------
# Recovery & Failure Classification Schemas
# -------------------------------------------------------------------------
class FailureCategory:
    """Standardized failure categories for agent actions."""

    TRANSIENT = "transient"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    PLUGIN_ERROR = "plugin_error"
    FATAL = "fatal"
    UNKNOWN = "unknown"


class RecoveryDecision:
    """Actions the recovery manager instructs the controller to take."""

    RETRY = "retry"
    REPLAN = "replan"
    WAIT_APPROVAL = "wait_approval"
    FAIL = "fail"
    SKIP = "skip"


class FailureClassification(BaseModel):
    """Detailed diagnosis and categorization of an action execution failure."""

    category: str = Field(
        default=FailureCategory.UNKNOWN,
        description="Category of the failure (transient, timeout, plugin_error, fatal, etc.)",
    )
    retryable: bool = Field(
        default=False,
        description="Whether this failure is deemed safe and reasonable to retry",
    )
    suggestion: Optional[str] = Field(
        default=None,
        description="Recommended correction or mitigation strategy",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic details extracted from the failure",
    )


# -------------------------------------------------------------------------
# Completion Evaluation Schema
# -------------------------------------------------------------------------
class CompletionEvaluation(BaseModel):
    """Comprehensive evaluation of task completion criteria."""

    is_complete: bool = Field(
        ...,
        description="Whether the task has truly and safely satisfied its requirements",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score in the evaluation outcome",
    )
    satisfied_requirements: List[str] = Field(
        default_factory=list,
        description="List of verified/satisfied goal requirements",
    )
    missing_requirements: List[str] = Field(
        default_factory=list,
        description="List of requirements or expected outputs not yet satisfied",
    )
    reason: str = Field(
        default="",
        description="Detailed explanation of the completion decision",
    )


# -------------------------------------------------------------------------
# Abstract Interfaces
# -------------------------------------------------------------------------
class Planner(ABC):
    """Interface for generating and adapting action plans."""

    @abstractmethod
    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """Generate an initial task execution plan for the given goal."""
        pass

    @abstractmethod
    def replan(self, state: TaskState, failure_reason: str) -> TaskPlan:
        """Generate an updated or alternative plan given current state and failure context."""
        pass

    async def aplan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """Asynchronously generate an initial task plan."""
        return await asyncio.to_thread(self.plan, goal, context)

    async def areplan(self, state: TaskState, failure_reason: str) -> TaskPlan:
        """Asynchronously replan given current state and failure context."""
        return await asyncio.to_thread(self.replan, state, failure_reason)


class Executor(ABC):
    """Interface for executing individual agent actions."""

    @abstractmethod
    def execute(
        self,
        action: Action,
        context: Optional[PluginExecutionContext] = None,
    ) -> ActionResult:
        """Synchronously execute a single action and return its structured outcome."""
        pass

    async def aexecute(
        self,
        action: Action,
        context: Optional[PluginExecutionContext] = None,
    ) -> ActionResult:
        """Asynchronously execute a single action."""
        return await asyncio.to_thread(self.execute, action, context)


class Observer(ABC):
    """Interface for observing action execution outcomes and updating perceptions."""

    @abstractmethod
    def observe(self, action: Action, result: ActionResult, state: TaskState) -> Observation:
        """Perceive the outcome of an action, interpret changes, and produce an Observation."""
        pass


class RecoveryManager(ABC):
    """Interface for failure classification, bounded retries, and replan routing."""

    @abstractmethod
    def classify_failure(
        self,
        action: Action,
        result: ActionResult,
        state: TaskState,
    ) -> FailureClassification:
        """Classify the failure into category, severity, and retryability."""
        pass

    @abstractmethod
    def handle_failure(
        self,
        action: Action,
        result: ActionResult,
        state: TaskState,
    ) -> str:
        """Determine next recovery action: RETRY, REPLAN, WAIT_APPROVAL, or FAIL."""
        pass

    @abstractmethod
    def can_retry(self, action: Action, state: TaskState) -> bool:
        """Check if the action can be retried within configured bounds."""
        pass

    def reset(self) -> None:
        """Reset internal tracking counters between tasks."""
        pass


class PermissionManager(ABC):
    """Interface for authorization checks and approval workflow."""

    @abstractmethod
    def get_permission_level(self, action: Action) -> PermissionLevel:
        """Determine whether an action is SAFE or REQUIRES_APPROVAL."""
        pass

    @abstractmethod
    def is_authorized(self, action: Action, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if an action is currently authorized to execute."""
        pass

    @abstractmethod
    def request_approval(self, action: Action, context: Optional[Dict[str, Any]] = None) -> bool:
        """Request explicit human or system approval for a consequential action."""
        pass


class CompletionEvaluator(ABC):
    """Interface for verifying task completion criteria."""

    @abstractmethod
    def evaluate(
        self,
        state: TaskState,
        verification_result: Optional[Any] = None,
    ) -> CompletionEvaluation:
        """Evaluate whether task requirements and quality gates have been satisfied."""
        pass


__all__ = [
    "FailureCategory",
    "RecoveryDecision",
    "FailureClassification",
    "CompletionEvaluation",
    "Planner",
    "Executor",
    "Observer",
    "RecoveryManager",
    "PermissionManager",
    "CompletionEvaluator",
]
