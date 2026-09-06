"""Task execution coordinator dispatching steps to registered Xeren plugins with timeouts, cancellation, and failure isolation."""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, Optional, Set

from xeren.plugins.automation.schemas import (
    StepRunRecord,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from xeren.plugins.automation.tools.retry import RetryManagerTool
from xeren.plugins.automation.tools.scheduler import BaseScheduler, DeterministicScheduler
from xeren.plugins.automation.tools.state import TaskStateManager
from xeren.plugins.contract import PluginExecutionResult
from xeren.plugins.errors import PluginError
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.plugins.automation.executor")


class TaskExecutorTool:
    """Coordinates execution of task DAGs through PluginManager with strict safety boundaries."""

    def __init__(
        self,
        state_manager: TaskStateManager,
        plugin_manager: Optional[PluginManager] = None,
        scheduler: Optional[BaseScheduler] = None,
        retry_manager: Optional[RetryManagerTool] = None,
        custom_dispatcher: Optional[Callable[[str, Any, Optional[float]], Any]] = None,
    ) -> None:
        self.state_manager = state_manager
        self.plugin_manager = plugin_manager
        self.scheduler = scheduler or DeterministicScheduler()
        self.retry_manager = retry_manager or RetryManagerTool()
        self.custom_dispatcher = custom_dispatcher

    def execute_task(
        self,
        task_id: str,
        timeout_seconds: Optional[float] = None,
    ) -> TaskPlan:
        """
        Synchronously execute all ready steps in a task DAG until complete, failed, paused, or cancelled.
        """
        plan = self.state_manager.get_plan(task_id)
        if not plan:
            raise ValueError(f"Task plan '{task_id}' not found.")

        if plan.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return plan

        max_timeout = timeout_seconds or plan.timeout_seconds or 300.0
        start_time = time.perf_counter()

        self.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        self.state_manager.add_history(task_id, "task_execution_started")

        completed_outputs: Dict[str, Any] = {
            s.id: s.output for s in plan.steps if s.status == StepStatus.COMPLETED and s.output is not None
        }

        while True:
            # Check elapsed time against task ceiling
            elapsed = time.perf_counter() - start_time
            if elapsed >= max_timeout:
                self.state_manager.update_task_status(task_id, TaskStatus.FAILED)
                self.state_manager.add_history(
                    task_id,
                    "task_timeout",
                    details={"elapsed_seconds": round(elapsed, 2), "timeout_limit": max_timeout},
                )
                break

            # Check if task was cancelled or paused
            if self.state_manager.is_cancelled(task_id):
                break
            if self.state_manager.is_paused(task_id):
                break

            # Refresh plan view
            current_plan = self.state_manager.get_plan(task_id)
            if not current_plan:
                break

            completed_ids: Set[str] = {
                s.id for s in current_plan.steps if s.status == StepStatus.COMPLETED
            }
            failed_ids: Set[str] = {
                s.id for s in current_plan.steps if s.status == StepStatus.FAILED
            }

            # Find next runnable steps
            runnable_steps = self.scheduler.get_next_runnable_steps(current_plan, completed_ids)

            if not runnable_steps:
                # Check termination conditions
                all_done = all(s.status == StepStatus.COMPLETED for s in current_plan.steps)
                any_fatal_failed = any(
                    s.status == StepStatus.FAILED and not s.is_optional for s in current_plan.steps
                )

                if all_done:
                    self.state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
                    self.state_manager.add_history(task_id, "task_completed")
                elif any_fatal_failed:
                    # Mark remaining pending steps as SKIPPED
                    for s in current_plan.steps:
                        if s.status in (StepStatus.PENDING, StepStatus.READY):
                            self.state_manager.update_step(task_id, s.id, {"status": StepStatus.SKIPPED})
                    self.state_manager.update_task_status(task_id, TaskStatus.FAILED)
                    self.state_manager.add_history(task_id, "task_failed")
                else:
                    # Check if pending steps are blocked by failed optional steps
                    has_pending = any(
                        s.status in (StepStatus.PENDING, StepStatus.READY) for s in current_plan.steps
                    )
                    if has_pending:
                        for s in current_plan.steps:
                            if s.status in (StepStatus.PENDING, StepStatus.READY):
                                self.state_manager.update_step(task_id, s.id, {"status": StepStatus.SKIPPED})
                        self.state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
                        self.state_manager.add_history(task_id, "task_completed_with_skipped_steps")
                    else:
                        self.state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
                        self.state_manager.add_history(task_id, "task_completed")
                break

            # Execute runnable step
            for step in runnable_steps:
                if self.state_manager.is_cancelled(task_id) or self.state_manager.is_paused(task_id):
                    break

                # Resolve dynamic inputs from dependency step outputs
                resolved_inputs = self.scheduler.resolve_inputs(step, completed_outputs)

                # Execute the step with isolated failure handling
                success, output, error, latency = self._execute_step(
                    task_id=task_id,
                    step=step,
                    resolved_inputs=resolved_inputs,
                )

                if success:
                    completed_outputs[step.id] = output
                elif not step.is_optional:
                    # If required step fails and retry exhausted, stop processing
                    break

        final_plan = self.state_manager.get_plan(task_id)
        return final_plan or plan

    async def aexecute_task(
        self,
        task_id: str,
        timeout_seconds: Optional[float] = None,
    ) -> TaskPlan:
        """Asynchronously execute the task plan."""
        return await asyncio.to_thread(self.execute_task, task_id, timeout_seconds)

    def _execute_step(
        self,
        task_id: str,
        step: TaskStep,
        resolved_inputs: Dict[str, Any],
    ) -> tuple[bool, Optional[Any], Optional[str], float]:
        """Execute a single atomic step, handling retries and updating state."""
        self.state_manager.update_step(
            task_id,
            step.id,
            {
                "status": StepStatus.RUNNING,
                "started_at": datetime.now(timezone.utc),
            },
        )
        self.state_manager.add_history(task_id, "step_started", step_id=step.id)

        step_timeout = step.timeout_seconds
        start = time.perf_counter()
        attempt = step.retry_count + 1

        try:
            output = self._dispatch_to_plugin(
                plugin_name=step.plugin_name,
                operation=step.operation,
                input_data=resolved_inputs,
                timeout=step_timeout,
            )
            latency = (time.perf_counter() - start) * 1000.0

            # Step succeeded
            self.state_manager.update_step(
                task_id,
                step.id,
                {
                    "status": StepStatus.COMPLETED,
                    "output": output,
                    "error": None,
                    "latency_ms": round(latency, 2),
                    "completed_at": datetime.now(timezone.utc),
                },
            )
            self.state_manager.add_run_record(
                task_id,
                StepRunRecord(
                    step_id=step.id,
                    run_index=attempt,
                    status=StepStatus.COMPLETED,
                    output=output,
                    latency_ms=round(latency, 2),
                ),
            )
            self.state_manager.add_history(task_id, "step_completed", step_id=step.id)
            return True, output, None, latency

        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            error_msg = str(exc)
            logger.warning("Step '%s' failed on attempt %d: %s", step.id, attempt, error_msg)

            # Record run record
            self.state_manager.add_run_record(
                task_id,
                StepRunRecord(
                    step_id=step.id,
                    run_index=attempt,
                    status=StepStatus.FAILED,
                    error=error_msg,
                    latency_ms=round(latency, 2),
                ),
            )

            # Check retry eligibility
            if self.retry_manager.should_retry(step, error=error_msg):
                backoff = self.retry_manager.compute_backoff(step)
                if backoff > 0.0:
                    time.sleep(backoff)

                retry_step = self.retry_manager.prepare_retry(step)
                self.state_manager.update_step(
                    task_id,
                    step.id,
                    {
                        "status": StepStatus.READY,
                        "retry_count": retry_step.retry_count,
                        "error": error_msg,
                        "latency_ms": round(latency, 2),
                    },
                )
                self.state_manager.add_history(
                    task_id,
                    "step_retry_scheduled",
                    step_id=step.id,
                    details={"attempt": retry_step.retry_count, "backoff": backoff},
                )
                # Re-dispatch immediately if eligible
                return self._execute_step(task_id, retry_step, resolved_inputs)

            # Retries exhausted or non-retryable
            self.state_manager.update_step(
                task_id,
                step.id,
                {
                    "status": StepStatus.FAILED,
                    "error": error_msg,
                    "latency_ms": round(latency, 2),
                    "completed_at": datetime.now(timezone.utc),
                },
            )
            self.state_manager.add_history(
                task_id,
                "step_failed",
                step_id=step.id,
                details={"error": error_msg},
            )
            return False, None, error_msg, latency

    def _dispatch_to_plugin(
        self,
        plugin_name: str,
        operation: str,
        input_data: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """Dispatch execution request to target plugin via PluginManager or custom dispatcher."""
        # 1. Check custom test dispatcher
        if self.custom_dispatcher:
            return self.custom_dispatcher(plugin_name, input_data, timeout)

        # 2. Check PluginManager
        if not self.plugin_manager:
            raise RuntimeError(f"No PluginManager configured; cannot invoke plugin '{plugin_name}'.")

        plugin = self.plugin_manager.get(plugin_name)
        if not plugin:
            raise RuntimeError(f"Plugin '{plugin_name}' is not registered in PluginManager.")

        # If operation key provided in payload, ensure it matches
        payload = dict(input_data)
        if "operation" not in payload and operation:
            payload["operation"] = operation

        # Execute target plugin
        exec_res: PluginExecutionResult = self.plugin_manager.execute(
            name=plugin_name,
            input_data=payload,
            timeout=timeout,
        )

        if not exec_res.success:
            raise PluginError(
                exec_res.error or f"Execution failed in plugin '{plugin_name}'."
            )

        return exec_res.output


__all__ = ["TaskExecutorTool"]
