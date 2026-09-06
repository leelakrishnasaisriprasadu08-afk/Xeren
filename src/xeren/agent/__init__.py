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
