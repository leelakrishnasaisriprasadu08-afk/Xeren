"""Xeren Plugin #9: Automation / Task Plugin.

Coordinates multi-step, multi-plugin execution workflows across Xeren plugins via DAG
dependency management, dynamic variable interpolation, bounded retries with backoff,
state tracking, pause/resume/cancel lifecycles, and audit logging.
"""

from xeren.plugins.automation.manifest import AUTOMATION_PLUGIN_MANIFEST
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.automation.registry import AutomationToolRegistry
from xeren.plugins.automation.schemas import (
    AutomationInput,
    AutomationOperation,
    AutomationResult,
    RetryPolicy,
    StepRunRecord,
    StepStatus,
    TaskHistoryEntry,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from xeren.plugins.automation.tools.executor import TaskExecutorTool
from xeren.plugins.automation.tools.planner import TaskPlannerError, TaskPlannerTool
from xeren.plugins.automation.tools.retry import RetryManagerTool
from xeren.plugins.automation.tools.scheduler import BaseScheduler, DeterministicScheduler
from xeren.plugins.automation.tools.state import TaskStateManager
from xeren.plugins.automation.workflow import AutomationWorkflow

__all__ = [
    "AutomationPlugin",
    "AUTOMATION_PLUGIN_MANIFEST",
    "AutomationToolRegistry",
    "AutomationWorkflow",
    "AutomationInput",
    "AutomationResult",
    "AutomationOperation",
    "TaskStatus",
    "StepStatus",
    "TaskStep",
    "TaskPlan",
    "RetryPolicy",
    "StepRunRecord",
    "TaskHistoryEntry",
    "TaskStateManager",
    "TaskPlannerTool",
    "TaskPlannerError",
    "DeterministicScheduler",
    "BaseScheduler",
    "RetryManagerTool",
    "TaskExecutorTool",
]
