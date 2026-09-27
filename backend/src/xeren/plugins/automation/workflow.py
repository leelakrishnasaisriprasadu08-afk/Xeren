"""Workflow orchestrator dispatching all 10 automation operations."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from xeren.plugins.automation.registry import AutomationToolRegistry
from xeren.plugins.automation.schemas import (
    AutomationInput,
    AutomationOperation,
    AutomationResult,
    StepStatus,
    TaskPlan,
    TaskStatus,
)
from xeren.plugins.automation.tools.planner import TaskPlannerError

logger = logging.getLogger("xeren.plugins.automation.workflow")


class AutomationWorkflow:
    """Orchestrates task creation, planning, execution, pause/resume, retry, cancellation, and history."""

    def __init__(self, registry: Optional[AutomationToolRegistry] = None) -> None:
        self.registry = registry or AutomationToolRegistry()

    def run(self, input_data: AutomationInput) -> AutomationResult:
        """Synchronously execute an automation operation."""
        start_time = time.perf_counter()
        op = input_data.operation

        handlers = {
            AutomationOperation.TASK_CREATE: self._execute_create,
            AutomationOperation.TASK_PLAN: self._execute_plan,
            AutomationOperation.TASK_EXECUTE: self._execute_run,
            AutomationOperation.TASK_PAUSE: self._execute_pause,
            AutomationOperation.TASK_RESUME: self._execute_resume,
            AutomationOperation.TASK_CANCEL: self._execute_cancel,
            AutomationOperation.TASK_STATUS: self._execute_status,
            AutomationOperation.TASK_RETRY: self._execute_retry,
            AutomationOperation.TASK_DEPENDENCY_MANAGEMENT: self._execute_dependency_management,
            AutomationOperation.TASK_HISTORY: self._execute_history,
            AutomationOperation.DESKTOP_LAUNCH: self._execute_desktop_launch,
            AutomationOperation.DESKTOP_COMMAND: self._execute_desktop_command,
            AutomationOperation.DESKTOP_LIST: self._execute_desktop_list,
            AutomationOperation.DESKTOP_TERMINATE: self._execute_desktop_terminate,
        }

        handler = handlers.get(op)
        if not handler:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return AutomationResult(
                operation=op,
                success=False,
                error=f"Unsupported automation operation: '{op}'",
                latency_ms=round(elapsed, 2),
            )

        try:
            res = handler(input_data)
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return res.model_copy(update={"latency_ms": round(elapsed, 2)})
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            logger.exception("Automation operation '%s' failed: %s", op, exc)
            return AutomationResult(
                operation=op,
                success=False,
                task_id=input_data.task_id,
                error=str(exc),
                latency_ms=round(elapsed, 2),
            )

    async def arun(self, input_data: AutomationInput) -> AutomationResult:
        """Asynchronously execute an automation operation."""
        return await asyncio.to_thread(self.run, input_data)

    # -------------------------------------------------------------------------
    # Handlers
    # -------------------------------------------------------------------------
    def _execute_create(self, input_data: AutomationInput) -> AutomationResult:
        objective = input_data.objective or "Unspecified task"
        steps = input_data.steps or []

        max_limit = input_data.max_steps or 50
        if steps and len(steps) > max_limit:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error=f"Task exceeds maximum step limit ({len(steps)} > {max_limit}).",
            )

        plan = self.registry.planner_tool.create_plan(
            objective=objective,
            steps=steps if steps else None,
            timeout_seconds=input_data.timeout_seconds or 300.0,
        )

        self.registry.state_manager.save_plan(plan)
        return AutomationResult(
            operation=input_data.operation,
            success=True,
            task_id=plan.task_id,
            status=plan.status,
            plan=plan,
        )

    def _execute_plan(self, input_data: AutomationInput) -> AutomationResult:
        objective = input_data.objective or (input_data.plan.objective if input_data.plan else "Multi-step plan")
        steps = input_data.steps or (input_data.plan.steps if input_data.plan else None)

        try:
            if steps:
                is_valid, error = self.registry.planner_tool.validate_dag(steps)
                if not is_valid:
                    return AutomationResult(
                        operation=input_data.operation,
                        success=False,
                        error=error,
                    )
                plan = TaskPlan(
                    objective=objective,
                    steps=steps,
                    timeout_seconds=input_data.timeout_seconds or 300.0,
                    status=TaskStatus.PLANNING,
                )
            else:
                plan = self.registry.planner_tool.plan_from_objective(objective)

            waves = self.registry.planner_tool.get_execution_waves(plan.steps)
            topological = [s.id for s in self.registry.planner_tool.get_topological_order(plan.steps)]

            return AutomationResult(
                operation=input_data.operation,
                success=True,
                task_id=plan.task_id,
                status=plan.status,
                plan=plan,
                metadata={
                    "total_steps": len(plan.steps),
                    "execution_waves": len(waves),
                    "topological_order": topological,
                },
            )
        except TaskPlannerError as exc:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error=str(exc),
            )

    def _execute_run(self, input_data: AutomationInput) -> AutomationResult:
        task_id = input_data.task_id

        # If existing task_id provided, fetch plan
        if task_id:
            plan = self.registry.state_manager.get_plan(task_id)
            if not plan:
                return AutomationResult(
                    operation=input_data.operation,
                    success=False,
                    task_id=task_id,
                    error=f"Task '{task_id}' not found.",
                )
        else:
            # Create a new plan from input
            if input_data.plan:
                plan = input_data.plan
            else:
                objective = input_data.objective or "Direct execution task"
                steps = input_data.steps or None
                plan = self.registry.planner_tool.create_plan(
                    objective=objective,
                    steps=steps,
                    timeout_seconds=input_data.timeout_seconds or 300.0,
                )
            self.registry.state_manager.save_plan(plan)
            task_id = plan.task_id

        # Execute plan
        final_plan = self.registry.executor_tool.execute_task(
            task_id=task_id,
            timeout_seconds=input_data.timeout_seconds,
        )

        step_results = {
            s.id: s.output for s in final_plan.steps if s.output is not None
        }
        history = self.registry.state_manager.get_history(task_id)
        success = final_plan.status == TaskStatus.COMPLETED

        error_msg: Optional[str] = None
        if not success:
            failed_errors = [s.error for s in final_plan.steps if s.status == StepStatus.FAILED and s.error]
            if failed_errors:
                error_msg = f"Task failed with step errors: {'; '.join(failed_errors)}"
            else:
                error_msg = f"Task finished with status '{final_plan.status.value}'."

        return AutomationResult(
            operation=input_data.operation,
            success=success,
            task_id=task_id,
            status=final_plan.status,
            plan=final_plan,
            step_results=step_results,
            history=history,
            error=error_msg,
        )

    def _execute_pause(self, input_data: AutomationInput) -> AutomationResult:
        if not input_data.task_id:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="task_id is required for TASK_PAUSE.",
            )
        success = self.registry.state_manager.pause_task(input_data.task_id)
        plan = self.registry.state_manager.get_plan(input_data.task_id)
        return AutomationResult(
            operation=input_data.operation,
            success=success,
            task_id=input_data.task_id,
            status=plan.status if plan else TaskStatus.FAILED,
            plan=plan,
            error=None if success else f"Could not pause task '{input_data.task_id}'.",
        )

    def _execute_resume(self, input_data: AutomationInput) -> AutomationResult:
        if not input_data.task_id:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="task_id is required for TASK_RESUME.",
            )
        success = self.registry.state_manager.resume_task(input_data.task_id)
        if not success:
            plan = self.registry.state_manager.get_plan(input_data.task_id)
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                task_id=input_data.task_id,
                status=plan.status if plan else TaskStatus.FAILED,
                error=f"Task '{input_data.task_id}' is not in PAUSED status.",
            )

        # Continue execution
        final_plan = self.registry.executor_tool.execute_task(
            task_id=input_data.task_id,
            timeout_seconds=input_data.timeout_seconds,
        )
        step_results = {s.id: s.output for s in final_plan.steps if s.output is not None}
        return AutomationResult(
            operation=input_data.operation,
            success=final_plan.status == TaskStatus.COMPLETED,
            task_id=input_data.task_id,
            status=final_plan.status,
            plan=final_plan,
            step_results=step_results,
        )

    def _execute_cancel(self, input_data: AutomationInput) -> AutomationResult:
        if not input_data.task_id:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="task_id is required for TASK_CANCEL.",
            )
        success = self.registry.state_manager.cancel_task(input_data.task_id)
        plan = self.registry.state_manager.get_plan(input_data.task_id)
        return AutomationResult(
            operation=input_data.operation,
            success=success,
            task_id=input_data.task_id,
            status=plan.status if plan else TaskStatus.FAILED,
            plan=plan,
            error=None if success else f"Could not cancel task '{input_data.task_id}'.",
        )

    def _execute_status(self, input_data: AutomationInput) -> AutomationResult:
        if not input_data.task_id:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="task_id is required for TASK_STATUS.",
            )
        plan = self.registry.state_manager.get_plan(input_data.task_id)
        if not plan:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                task_id=input_data.task_id,
                error=f"Task '{input_data.task_id}' not found.",
            )
        step_results = {s.id: s.output for s in plan.steps if s.output is not None}
        history = self.registry.state_manager.get_history(input_data.task_id)
        return AutomationResult(
            operation=input_data.operation,
            success=True,
            task_id=input_data.task_id,
            status=plan.status,
            plan=plan,
            step_results=step_results,
            history=history,
        )

    def _execute_retry(self, input_data: AutomationInput) -> AutomationResult:
        if not input_data.task_id:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="task_id is required for TASK_RETRY.",
            )
        plan = self.registry.state_manager.get_plan(input_data.task_id)
        if not plan:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                task_id=input_data.task_id,
                error=f"Task '{input_data.task_id}' not found.",
            )

        # If specific step_id requested, reset that step
        target_step_id = input_data.step_id
        for s in plan.steps:
            if target_step_id:
                if s.id == target_step_id:
                    self.registry.state_manager.update_step(
                        input_data.task_id,
                        s.id,
                        {"status": StepStatus.READY, "error": None},
                    )
            elif s.status in (StepStatus.FAILED, StepStatus.SKIPPED):
                self.registry.state_manager.update_step(
                    input_data.task_id,
                    s.id,
                    {"status": StepStatus.READY, "error": None},
                )

        # Resume / restart execution
        self.registry.state_manager.update_task_status(input_data.task_id, TaskStatus.RUNNING)
        final_plan = self.registry.executor_tool.execute_task(
            task_id=input_data.task_id,
            timeout_seconds=input_data.timeout_seconds,
        )
        step_results = {s.id: s.output for s in final_plan.steps if s.output is not None}
        return AutomationResult(
            operation=input_data.operation,
            success=final_plan.status == TaskStatus.COMPLETED,
            task_id=input_data.task_id,
            status=final_plan.status,
            plan=final_plan,
            step_results=step_results,
        )

    def _execute_dependency_management(self, input_data: AutomationInput) -> AutomationResult:
        steps = input_data.steps
        task_id = input_data.task_id
        if not steps and task_id:
            plan = self.registry.state_manager.get_plan(task_id)
            if plan:
                steps = plan.steps

        if not steps:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="No steps or task_id provided to inspect dependencies.",
            )

        is_valid, error = self.registry.planner_tool.validate_dag(steps)
        if not is_valid:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error=error,
                metadata={"valid_dag": False, "is_acyclic": False},
            )

        waves = self.registry.planner_tool.get_execution_waves(steps)
        topological = [s.id for s in self.registry.planner_tool.get_topological_order(steps)]

        dep_map = {s.id: s.depends_on for s in steps}
        return AutomationResult(
            operation=input_data.operation,
            success=True,
            task_id=task_id,
            metadata={
                "valid_dag": True,
                "is_acyclic": True,
                "dependency_map": dep_map,
                "execution_waves": [[s.id for s in wave] for wave in waves],
                "topological_order": topological,
            },
        )

    def _execute_history(self, input_data: AutomationInput) -> AutomationResult:
        if not input_data.task_id:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="task_id is required for TASK_HISTORY.",
            )
        history = self.registry.state_manager.get_history(input_data.task_id)
        run_records = self.registry.state_manager.get_run_records(input_data.task_id)
        plan = self.registry.state_manager.get_plan(input_data.task_id)

        return AutomationResult(
            operation=input_data.operation,
            success=True,
            task_id=input_data.task_id,
            status=plan.status if plan else TaskStatus.PENDING,
            plan=plan,
            history=history,
            metadata={
                "run_records_count": len(run_records),
                "run_records": [r.model_dump(mode="python") for r in run_records],
            },
        )

    def _execute_desktop_launch(self, input_data: AutomationInput) -> AutomationResult:
        app_name = input_data.app_name or (input_data.metadata.get("app_name") if input_data.metadata else None)
        if not app_name:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="app_name is required for DESKTOP_LAUNCH.",
            )
        args = input_data.app_args or (input_data.metadata.get("args") if input_data.metadata else None)
        cwd = input_data.cwd or (input_data.metadata.get("cwd") if input_data.metadata else None)
        res = self.registry.desktop_operator.launch_app(app_name, args=args, cwd=cwd)
        return AutomationResult(
            operation=input_data.operation,
            success=res.get("success", False),
            error=res.get("error"),
            metadata=res,
        )

    def _execute_desktop_command(self, input_data: AutomationInput) -> AutomationResult:
        cmd = input_data.command or input_data.objective or (input_data.metadata.get("command") if input_data.metadata else None)
        if not cmd:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="command string is required for DESKTOP_COMMAND.",
            )
        timeout = input_data.timeout_seconds or 30.0
        cwd = input_data.cwd or (input_data.metadata.get("cwd") if input_data.metadata else None)
        res = self.registry.desktop_operator.execute_shell(cmd, timeout=timeout, cwd=cwd)
        return AutomationResult(
            operation=input_data.operation,
            success=res.get("success", False),
            error=res.get("stderr") if not res.get("success") else None,
            metadata=res,
        )

    def _execute_desktop_list(self, input_data: AutomationInput) -> AutomationResult:
        filter_name = input_data.app_name or (input_data.metadata.get("filter_name") if input_data.metadata else None)
        apps = self.registry.desktop_operator.list_running_apps(filter_name=filter_name)
        return AutomationResult(
            operation=input_data.operation,
            success=True,
            metadata={"apps": apps, "count": len(apps)},
        )

    def _execute_desktop_terminate(self, input_data: AutomationInput) -> AutomationResult:
        target = input_data.pid or input_data.app_name or (input_data.metadata.get("target") if input_data.metadata else None)
        if not target:
            return AutomationResult(
                operation=input_data.operation,
                success=False,
                error="pid or app_name is required for DESKTOP_TERMINATE.",
            )
        force = bool(input_data.metadata.get("force", False)) if input_data.metadata else False
        res = self.registry.desktop_operator.terminate_app(target, force=force)
        return AutomationResult(
            operation=input_data.operation,
            success=res.get("success", False),
            error=res.get("error"),
            metadata=res,
        )


__all__ = ["AutomationWorkflow"]
