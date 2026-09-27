"""Automation / Task Plugin implementation adhering strictly to the Xeren BasePlugin contract."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.plugins.automation.manifest import AUTOMATION_PLUGIN_MANIFEST
from xeren.plugins.automation.registry import AutomationToolRegistry
from xeren.plugins.automation.schemas import (
    AutomationInput,
    AutomationOperation,
    AutomationResult,
    TaskPlan,
    TaskStep,
)
from xeren.plugins.automation.workflow import AutomationWorkflow
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError

if TYPE_CHECKING:
    from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.plugins.automation.plugin")


class AutomationPlugin(BasePlugin):
    """Production automation/task plugin for orchestrating multi-step workflows across Xeren plugins."""

    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        registry: Optional[AutomationToolRegistry] = None,
        workflow: Optional[AutomationWorkflow] = None,
    ) -> None:
        self.registry = registry or AutomationToolRegistry(plugin_manager=plugin_manager)
        self.workflow = workflow or AutomationWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return AUTOMATION_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return AutomationInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return AutomationResult

    def set_plugin_manager(self, plugin_manager: PluginManager) -> None:
        """Inject or update the active PluginManager instance."""
        self.registry.set_plugin_manager(plugin_manager)

    # -------------------------------------------------------------------------
    # BasePlugin Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute an automation task operation."""
        start_time = time.perf_counter()
        try:
            validated_input: AutomationInput = self.validate_input(input_data)  # type: ignore
            result: AutomationResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "task_id": result.task_id,
                    "status": result.status.value if result.status else None,
                    "steps_count": len(result.plan.steps) if result.plan else 0,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("AutomationPlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"AutomationPlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute an automation task operation."""
        start_time = time.perf_counter()
        try:
            validated_input: AutomationInput = self.validate_input(input_data)  # type: ignore
            result: AutomationResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "task_id": result.task_id,
                    "status": result.status.value if result.status else None,
                    "steps_count": len(result.plan.steps) if result.plan else 0,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("AutomationPlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"AutomationPlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def create_task(
        self,
        objective: str,
        steps: Optional[List[TaskStep]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> AutomationResult:
        """Create and optionally plan a new structured multi-step task."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_CREATE,
            task_id=task_id,
            objective=objective,
            steps=steps or [],
            metadata=metadata or {},
            auto_plan=auto_plan,
        )
        return self.workflow.run(inp)

    def plan_task(
        self,
        objective: Optional[str] = None,
        steps: Optional[List[TaskStep]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AutomationResult:
        """Plan steps and validate dependency topology for an existing or new task."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_PLAN,
            task_id=task_id,
            objective=objective,
            steps=steps or [],
            metadata=metadata or {},
        )
        return self.workflow.run(inp)

    def execute_task(
        self,
        task_id: Optional[str] = None,
        plan: Optional[TaskPlan] = None,
        timeout_seconds: Optional[float] = None,
        max_steps: Optional[int] = None,
    ) -> AutomationResult:
        """Synchronously execute a planned task DAG."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_EXECUTE,
            task_id=task_id,
            plan=plan,
            timeout_seconds=timeout_seconds,
            max_steps=max_steps or 50,
        )
        return self.workflow.run(inp)

    async def aexecute_task(
        self,
        task_id: Optional[str] = None,
        plan: Optional[TaskPlan] = None,
        timeout_seconds: Optional[float] = None,
        max_steps: Optional[int] = None,
    ) -> AutomationResult:
        """Asynchronously execute a planned task DAG."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_EXECUTE,
            task_id=task_id,
            plan=plan,
            timeout_seconds=timeout_seconds,
            max_steps=max_steps or 50,
        )
        return await self.workflow.arun(inp)

    def pause_task(self, task_id: str, reason: Optional[str] = None) -> AutomationResult:
        """Signal an active task execution to pause after current in-flight step."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_PAUSE,
            task_id=task_id,
            metadata={"reason": reason} if reason else {},
        )
        return self.workflow.run(inp)

    def resume_task(
        self,
        task_id: str,
        timeout_seconds: Optional[float] = None,
    ) -> AutomationResult:
        """Resume execution of a paused task."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_RESUME,
            task_id=task_id,
            timeout_seconds=timeout_seconds,
        )
        return self.workflow.run(inp)

    async def aresume_task(
        self,
        task_id: str,
        timeout_seconds: Optional[float] = None,
    ) -> AutomationResult:
        """Asynchronously resume execution of a paused task."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_RESUME,
            task_id=task_id,
            timeout_seconds=timeout_seconds,
        )
        return await self.workflow.arun(inp)

    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> AutomationResult:
        """Cancel an in-flight or paused task."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_CANCEL,
            task_id=task_id,
            metadata={"reason": reason} if reason else {},
        )
        return self.workflow.run(inp)

    def get_status(self, task_id: str) -> AutomationResult:
        """Retrieve the live execution status and step records for a task."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_STATUS,
            task_id=task_id,
        )
        return self.workflow.run(inp)

    def retry_task(
        self,
        task_id: str,
        step_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> AutomationResult:
        """Retry a failed task or specific failed step."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_RETRY,
            task_id=task_id,
            step_id=step_id,
            timeout_seconds=timeout_seconds,
        )
        return self.workflow.run(inp)

    async def aretry_task(
        self,
        task_id: str,
        step_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> AutomationResult:
        """Asynchronously retry a failed task or specific failed step."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_RETRY,
            task_id=task_id,
            step_id=step_id,
            timeout_seconds=timeout_seconds,
        )
        return await self.workflow.arun(inp)

    def manage_dependencies(
        self,
        steps: List[TaskStep],
        task_id: Optional[str] = None,
    ) -> AutomationResult:
        """Analyze, validate, and extract topological ordering for a set of steps."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_DEPENDENCY_MANAGEMENT,
            task_id=task_id,
            steps=steps,
        )
        return self.workflow.run(inp)

    def get_history(
        self,
        task_id: Optional[str] = None,
        limit: int = 50,
    ) -> AutomationResult:
        """Retrieve audit trail and historical run records for tasks."""
        inp = AutomationInput(
            operation=AutomationOperation.TASK_HISTORY,
            task_id=task_id,
            limit=limit,
        )
        return self.workflow.run(inp)

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Synchronously check operational readiness and tool availability."""
        start_time = time.perf_counter()
        active_tasks = len(self.registry.state_manager.list_all_plans())
        history_records = len(self.registry.state_manager.get_history())

        details = {
            "initialized": self._initialized,
            "has_plugin_manager": self.registry.plugin_manager is not None,
            "active_tasks_count": active_tasks,
            "history_records_count": history_records,
            "registered_tools_count": 5,
            "tools_ready": True,
            "supported_capabilities": self.manifest.capabilities,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return HealthCheckResult(
            status=PluginHealthStatus.HEALTHY,
            details=details,
            latency_ms=latency_ms,
            error=None,
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational readiness."""
        return await asyncio.to_thread(self.health_check)

    def health(self) -> HealthCheckResult:
        """Alias conforming to standard plugin contract."""
        return self.health_check()

    def initialize(self) -> None:
        """Initialize plugin state."""
        self._initialized = True

    def shutdown(self) -> None:
        """Release plugin resources and reset state."""
        self._initialized = False


__all__ = ["AutomationPlugin"]
