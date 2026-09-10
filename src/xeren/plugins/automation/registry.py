"""Tool registry for Automation Plugin coordinating state, planner, scheduler, retry, and executor."""

from typing import Any, Callable, Optional

from xeren.plugins.automation.tools.desktop import WindowsDesktopOperator
from xeren.plugins.automation.tools.executor import TaskExecutorTool
from xeren.plugins.automation.tools.planner import TaskPlannerTool
from xeren.plugins.automation.tools.retry import RetryManagerTool
from xeren.plugins.automation.tools.scheduler import BaseScheduler, DeterministicScheduler
from xeren.plugins.automation.tools.state import TaskStateManager
from xeren.plugins.manager import PluginManager


class AutomationToolRegistry:
    """Central registry and lifecycle manager for automation tools and execution dependencies."""

    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        state_manager: Optional[TaskStateManager] = None,
        planner_tool: Optional[TaskPlannerTool] = None,
        scheduler_tool: Optional[BaseScheduler] = None,
        retry_tool: Optional[RetryManagerTool] = None,
        desktop_operator: Optional[WindowsDesktopOperator] = None,
        custom_dispatcher: Optional[Callable[[str, Any, Optional[float]], Any]] = None,
    ) -> None:
        self.state_manager = state_manager or TaskStateManager()
        self.planner_tool = planner_tool or TaskPlannerTool()
        self.scheduler_tool = scheduler_tool or DeterministicScheduler()
        self.retry_tool = retry_tool or RetryManagerTool()
        self.desktop_operator = desktop_operator or WindowsDesktopOperator()
        self.executor_tool = TaskExecutorTool(
            state_manager=self.state_manager,
            plugin_manager=plugin_manager,
            scheduler=self.scheduler_tool,
            retry_manager=self.retry_tool,
            custom_dispatcher=custom_dispatcher,
        )

    @property
    def plugin_manager(self) -> Optional[PluginManager]:
        """Active PluginManager reference on executor."""
        return self.executor_tool.plugin_manager

    def set_plugin_manager(self, plugin_manager: PluginManager) -> None:
        """Update PluginManager reference on executor."""
        self.executor_tool.plugin_manager = plugin_manager

    def set_custom_dispatcher(
        self, dispatcher: Optional[Callable[[str, Any, Optional[float]], Any]]
    ) -> None:
        """Set mock dispatcher for testing."""
        self.executor_tool.custom_dispatcher = dispatcher


__all__ = ["AutomationToolRegistry"]
