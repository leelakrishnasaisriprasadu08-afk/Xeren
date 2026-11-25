"""Xeren Autonomous Work Agent subsystem.

Provides an autonomous task-execution runtime with pluggable planning,
execution, perception, recovery, permissions, and outcome learning.
"""

from xeren.agent.actions import (
    Action,
    ActionResult,
    ActionType,
    PermissionLevel,
)
from xeren.agent.browser import (
    BaseBrowserAdapter,
    BrowserAction,
    BrowserActionType,
    BrowserInput,
    BrowserObservation,
    BrowserPlugin,
    BrowserResult,
    MockBrowserAdapter,
)
from xeren.agent.controller import AgentController
from xeren.agent.evaluator import DefaultCompletionEvaluator
from xeren.agent.executor import AgentExecutor
from xeren.agent.interfaces import (
    CompletionEvaluation,
    CompletionEvaluator,
    Executor,
    FailureCategory,
    FailureClassification,
    Observer,
    PermissionManager,
    Planner,
    RecoveryDecision,
    RecoveryManager,
)
from xeren.agent.observer import DefaultObserver
from xeren.agent.permissions import DefaultPermissionManager
from xeren.agent.planner import (
    CorePlannerAdapter,
    MockPlanner,
    TaskPlan,
)
from xeren.agent.validator import (
    PlanValidationError,
    PlanValidationResult,
    PlanValidator,
)

"""Xeren Autonomous Work Agent with Browser Automation."""

from xeren.agent.browser import (
    BaseBrowserAdapter,
    BrowserActionError,
    BrowserAdapterError,
    BrowserElementNotFoundError,
    BrowserNavigationError,
    BrowserSecurityError,
    BrowserSecurityManager,
    BrowserSessionError,
    BrowserTimeoutError,
    MockBrowserAdapter,
    PlaywrightBrowserAdapter,
)
from xeren.agent.controller import AgentController
from xeren.agent.evaluator import EvaluationResult, Evaluator
from xeren.agent.executor import Executor
from xeren.agent.observer import Observer
from xeren.agent.permissions import PermissionManager, PermissionMode
from xeren.agent.planner import Planner
from xeren.agent.plugins import (
    ExperienceInput,
    ExperienceOutput,
    ExperiencePlugin,
    VerificationInput,
    VerificationOutput,
    VerificationPlugin,
)
from xeren.agent.recovery import DefaultRecoveryManager
from xeren.agent.state import (
    Observation,
    TaskState,
    TaskStatus,
)

__all__ = [
    # State & Status
    "TaskStatus",
    "TaskState",
    "Observation",
    # Actions
    "Action",
    "ActionResult",
    "ActionType",
    "PermissionLevel",
    # Planner
    "Planner",
    "TaskPlan",
    "MockPlanner",
    "CorePlannerAdapter",
    "PlanValidator",
    "PlanValidationResult",
    "PlanValidationError",
    # Executor & Observer
    "Executor",
    "AgentExecutor",
    "Observer",
    "DefaultObserver",
    # Recovery
    "RecoveryManager",
    "DefaultRecoveryManager",
    "FailureCategory",
    "FailureClassification",
    "RecoveryDecision",
    # Permissions
    "PermissionManager",
    "DefaultPermissionManager",
    # Evaluator
    "CompletionEvaluator",
    "DefaultCompletionEvaluator",
    "CompletionEvaluation",
    # Controller
    "AgentController",
    # Browser
    "BaseBrowserAdapter",
    "MockBrowserAdapter",
    "BrowserAction",
    "BrowserActionType",
    "BrowserObservation",
    "BrowserPlugin",
    "BrowserInput",
    "BrowserResult",
    # Verification & Experience Plugins
]

from xeren.agent.recovery import RecoveryManager, RecoveryStrategy
from xeren.agent.types import (
    ActionCategory,
    ActionResult,
    AgentAction,
    AgentState,
    AgentStatus,
    BrowserActionType,
    BrowserError,
    BrowserObservation,
    InteractiveElement,
)

__all__ = [
    # Core Controller & Subsystems
    "AgentController",
    "Planner",
    "Executor",
    "Observer",
    "RecoveryManager",
    "RecoveryStrategy",
    "PermissionManager",
    "PermissionMode",
    "Evaluator",
    "EvaluationResult",
    # Browser Adapters & Contracts
    "BaseBrowserAdapter",
    "MockBrowserAdapter",
    "PlaywrightBrowserAdapter",
    "BrowserSecurityManager",
    "BrowserAdapterError",
    "BrowserNavigationError",
    "BrowserTimeoutError",
    "BrowserElementNotFoundError",
    "BrowserSecurityError",
    "BrowserSessionError",
    "BrowserActionError",
    # Data Types & Schemas
    "AgentAction",
    "ActionResult",
    "AgentState",
    "AgentStatus",
    "ActionCategory",
    "BrowserObservation",
    "BrowserError",
    "InteractiveElement",
    "BrowserActionType",
    # Agent Plugins
    "VerificationPlugin",
    "VerificationInput",
    "VerificationOutput",
    "ExperiencePlugin",
    "ExperienceInput",
    "ExperienceOutput",
]
