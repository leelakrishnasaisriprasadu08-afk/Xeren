"""AgentController: The central autonomous work agent runtime coordinator."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from xeren.agent.actions import Action, ActionResult, PermissionLevel
from xeren.agent.evaluator import DefaultCompletionEvaluator
from xeren.agent.executor import AgentExecutor
from xeren.agent.interfaces import (
    CompletionEvaluator,
    Executor,
    Observer,
    PermissionManager,
    Planner,
    RecoveryDecision,
    RecoveryManager,
)
from xeren.agent.observer import DefaultObserver
from xeren.agent.permissions import DefaultPermissionManager
from xeren.agent.planner import MockPlanner
from xeren.agent.plugins.experience import ExperiencePlugin
from xeren.agent.plugins.verification import VerificationPlugin
from xeren.agent.recovery import DefaultRecoveryManager
from xeren.agent.state import TaskState, TaskStatus
from xeren.data.schema import VerificationDetails

"""Central AgentController orchestrating Planner, Executor, Observer, Recovery, and Permissions."""

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.evaluator import Evaluator
from xeren.agent.executor import Executor
from xeren.agent.observer import Observer
from xeren.agent.permissions import PermissionManager
from xeren.agent.planner import Planner
from xeren.agent.recovery import RecoveryManager, RecoveryStrategy
from xeren.agent.types import AgentAction, AgentState, AgentStatus
 main
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.agent.controller")


class AgentController:
 feature/core-architecture
    """High-level autonomous task execution controller.

    Coordinates the autonomous execution loop:
    PLAN → SELECT ACTION → PERMISSION CHECK → EXECUTE → OBSERVE → EVALUATE → CONTINUE / RETRY / REPLAN / COMPLETE / STOP.
    """

    def __init__(
        self,

    """Central orchestrator driving autonomous goal execution loops."""

    def __init__(
        self,
        browser_adapter: BaseBrowserAdapter,
 main
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        observer: Optional[Observer] = None,
        recovery_manager: Optional[RecoveryManager] = None,
        permission_manager: Optional[PermissionManager] = None,
 feature/core-architecture
        completion_evaluator: Optional[CompletionEvaluator] = None,
        plugin_manager: Optional[PluginManager] = None,
        verification_plugin: Optional[VerificationPlugin] = None,
        experience_plugin: Optional[ExperiencePlugin] = None,
        workspace_manager: Optional[Any] = None,
        max_total_cycles: int = 50,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.plugin_manager = plugin_manager if plugin_manager is not None else PluginManager()
        self.workspace_manager = workspace_manager
        self.planner = planner if planner is not None else MockPlanner()
        self.executor = executor if executor is not None else AgentExecutor(self.plugin_manager, workspace_manager=workspace_manager)
        self.observer = observer if observer is not None else DefaultObserver()
        self.recovery_manager = recovery_manager if recovery_manager is not None else DefaultRecoveryManager(max_total_cycles=max_total_cycles)
        self.permission_manager = permission_manager if permission_manager is not None else DefaultPermissionManager()
        self.completion_evaluator = completion_evaluator if completion_evaluator is not None else DefaultCompletionEvaluator()

        # Optional Verification and Experience integrations
        self.verification_plugin = verification_plugin if verification_plugin is not None else self._find_verification_plugin()
        self.experience_plugin = experience_plugin if experience_plugin is not None else self._find_experience_plugin()

        self.max_total_cycles = max_total_cycles
        self.timeout_seconds = timeout_seconds
        self._cancelled: bool = False
        self._last_verification: Optional[VerificationDetails] = None

    def _find_verification_plugin(self) -> Optional[VerificationPlugin]:
        """Discover VerificationPlugin if registered with PluginManager."""
        p = self.plugin_manager.get("verification")
        if isinstance(p, VerificationPlugin):
            return p
        return None

    def _find_experience_plugin(self) -> Optional[ExperiencePlugin]:
        """Discover ExperiencePlugin if registered with PluginManager."""
        p = self.plugin_manager.get("experience")
        if isinstance(p, ExperiencePlugin):
            return p
        return None

    def cancel(self) -> None:
        """Signal cancellation to halt the execution loop."""
        logger.info("Cancellation requested for active agent execution.")
        self._cancelled = True

    def reset_cancellation(self) -> None:
        """Reset the cancellation flag for subsequent runs."""
        self._cancelled = False

    def run(
        self,
        goal: str,
        initial_artifacts: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> TaskState:
        """Synchronously execute an autonomous task from goal to completion."""
        start_time = time.perf_counter()
        effective_timeout = timeout or self.timeout_seconds

        # 1. PLAN: Initialize TaskState and formulate initial plan
        state = self._initialize_task(goal, initial_artifacts, metadata)
        logger.info("Starting autonomous task '%s' for goal: %s", state.task_id, goal)

        plan = self.planner.plan(goal=goal, context=state.metadata)
        state.remaining_steps = list(plan.steps)
        state.status = TaskStatus.RUNNING
        state.metadata["plan_id"] = plan.plan_id

        # 2. LOOP: Execute steps until terminal status reached
        while not state.is_terminal:
            # Check cancellation
            if self._cancelled:
                state.status = TaskStatus.CANCELLED
                state.metadata["cancellation_reason"] = "Task was explicitly cancelled by user/system"
                break

            # Check timeout
            elapsed = time.perf_counter() - start_time
            if effective_timeout is not None and elapsed > effective_timeout:
                logger.warning("Task '%s' timed out after %.2fs", state.task_id, elapsed)
                state.status = TaskStatus.TIMED_OUT
                state.metadata["timeout_seconds"] = effective_timeout
                break

            # Check total execution cycles
            if state.attempt_count >= self.max_total_cycles:
                logger.error("Task '%s' reached cycle limit (%d). Terminating safely.", state.task_id, self.max_total_cycles)
                state.status = TaskStatus.FAILED
                state.metadata["failure_reason"] = f"Max execution cycles ({self.max_total_cycles}) exceeded"
                break

            # Execute a single step
            state = self.step(state)

            # If waiting for approval, pause execution and break loop for external authorization
            if state.status == TaskStatus.WAITING_APPROVAL:
                logger.info("Task '%s' paused awaiting approval.", state.task_id)
                break

        # 3. Post-execution finalization: Verification & Experience recording
        self._finalize_task(state)
        return state

    async def arun(
        self,
        goal: str,
        initial_artifacts: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> TaskState:
        """Asynchronously execute an autonomous task from goal to completion."""
        start_time = time.perf_counter()
        effective_timeout = timeout or self.timeout_seconds

        state = self._initialize_task(goal, initial_artifacts, metadata)
        logger.info("Starting async autonomous task '%s' for goal: %s", state.task_id, goal)

        plan = await self.planner.aplan(goal=goal, context=state.metadata)
        state.remaining_steps = list(plan.steps)
        state.status = TaskStatus.RUNNING
        state.metadata["plan_id"] = plan.plan_id

        while not state.is_terminal:
            if self._cancelled:
                state.status = TaskStatus.CANCELLED
                state.metadata["cancellation_reason"] = "Task was explicitly cancelled"
                break

            elapsed = time.perf_counter() - start_time
            if effective_timeout is not None and elapsed > effective_timeout:
                state.status = TaskStatus.TIMED_OUT
                state.metadata["timeout_seconds"] = effective_timeout
                break

            if state.attempt_count >= self.max_total_cycles:
                state.status = TaskStatus.FAILED
                state.metadata["failure_reason"] = f"Max execution cycles ({self.max_total_cycles}) exceeded"
                break

            state = await self.astep(state)

            if state.status == TaskStatus.WAITING_APPROVAL:
                break

        self._finalize_task(state)
        return state

    def step(self, state: TaskState) -> TaskState:
        """Execute a single cycle of the autonomous task loop."""
        if state.is_terminal:
            return state

        # If no remaining steps, evaluate completion or replan
        if not state.remaining_steps:
            return self._evaluate_and_complete(state)

        # 1. SELECT ACTION
        action = state.remaining_steps[0]
        state.current_step = action

        # 2. PERMISSION CHECK
        permission_level = self.permission_manager.get_permission_level(action)
        action.permission_level = permission_level

        if permission_level == PermissionLevel.REQUIRES_APPROVAL:
            if not self.permission_manager.is_authorized(action, state.metadata):
                approved = self.permission_manager.request_approval(action, state.metadata)
                if not approved:
                    logger.warning("Action '%s' requires approval and was not granted.", action.action_id)
                    state.status = TaskStatus.WAITING_APPROVAL
                    auth_err = f"Action '{action.action_id}' on '{action.target}' requires approval and is not authorized."
                    res = ActionResult(
                        action_id=action.action_id,
                        success=False,
                        error=auth_err,
                        metadata={"target": action.target, "permission_level": permission_level.value},
                    )
                    state.record_failure(action, res)
                    return state

        # 3. EXECUTE
        state.attempt_count += 1
        state.status = TaskStatus.RUNNING
        res = self.executor.execute(action)

        # 4. OBSERVE
        obs = self.observer.observe(action, res, state)
        state.record_observation(obs)

        # 5. EVALUATE & DECIDE (SUCCESS / RETRY / REPLAN / FAIL)
        return self._process_step_result(state, action, res)

    async def astep(self, state: TaskState) -> TaskState:
        """Asynchronously execute a single cycle of the autonomous task loop."""
        if state.is_terminal:
            return state

        if not state.remaining_steps:
            return self._evaluate_and_complete(state)

        action = state.remaining_steps[0]
        state.current_step = action

        permission_level = self.permission_manager.get_permission_level(action)
        action.permission_level = permission_level

        if permission_level == PermissionLevel.REQUIRES_APPROVAL:
            if not self.permission_manager.is_authorized(action, state.metadata):
                approved = self.permission_manager.request_approval(action, state.metadata)
                if not approved:
                    state.status = TaskStatus.WAITING_APPROVAL
                    res = ActionResult(
                        action_id=action.action_id,
                        success=False,
                        error=f"Action '{action.action_id}' requires approval and is not authorized.",
                        metadata={"target": action.target},
                    )
                    state.record_failure(action, res)
                    return state

        state.attempt_count += 1
        state.status = TaskStatus.RUNNING
        res = await self.executor.aexecute(action)

        obs = self.observer.observe(action, res, state)
        state.record_observation(obs)

        return self._process_step_result(state, action, res)

    def _process_step_result(
        self,
        state: TaskState,
        action: Action,
        result: ActionResult,
    ) -> TaskState:
        """Process the outcome of an action execution, handling success or failure recovery."""
        if result.success:
            state.record_success(action, result)

            # If this was the last planned step, evaluate task completion
            if not state.remaining_steps:
                return self._evaluate_and_complete(state)

            state.status = TaskStatus.RUNNING
            return state

        # Action Failed -> Route through RecoveryManager
        state.record_failure(action, result)
        decision = self.recovery_manager.handle_failure(action, result, state)
        state.metadata["last_recovery_decision"] = decision

        if decision == RecoveryDecision.RETRY:
            state.status = TaskStatus.RECOVERING
            logger.info("RecoveryDecision: RETRY for action '%s'", action.action_id)
            return state

        elif decision == RecoveryDecision.REPLAN:
            state.status = TaskStatus.RECOVERING
            replan_reason = result.error or "Action execution failed"
            logger.info("RecoveryDecision: REPLAN for task '%s'. Reason: %s", state.task_id, replan_reason)
            new_plan = self.planner.replan(state, replan_reason)
            if new_plan.steps:
                state.remaining_steps = list(new_plan.steps)
                state.current_step = None
                state.metadata["replanned"] = True
            else:
                state.status = TaskStatus.FAILED
                state.metadata["failure_reason"] = f"Replan returned no alternative steps. Error: {replan_reason}"
            return state

        elif decision == RecoveryDecision.WAIT_APPROVAL:
            state.status = TaskStatus.WAITING_APPROVAL
            return state

        else:  # RecoveryDecision.FAIL or unrecoverable
            state.status = TaskStatus.FAILED
            state.metadata["failure_reason"] = result.error or "Execution failed and recovery is impossible"
            return state

    def _evaluate_and_complete(self, state: TaskState) -> TaskState:
        """Run verification gate and evaluate if task requirements have been satisfied."""
        # 1. Run Verification Plugin if available
        verif_result: Optional[VerificationDetails] = None
        if self.verification_plugin is not None:
            try:
                verif_result = self.verification_plugin.verify_artifacts(
                    task=state.goal,
                    artifacts=state.artifacts,
                    rules=state.metadata.get("verification_rules", []),
                )
                self._last_verification = verif_result
                state.metadata["verification"] = verif_result.model_dump()
            except Exception as err:
                logger.warning("Verification check encountered error: %s", err)

        # 2. Evaluate Completion
        evaluation = self.completion_evaluator.evaluate(state, verif_result)
        state.metadata["completion_evaluation"] = evaluation.model_dump()

        if evaluation.is_complete:
            state.status = TaskStatus.COMPLETED
            logger.info("Task '%s' successfully COMPLETED!", state.task_id)
            return state

        # Not complete: check if replan can satisfy missing requirements
        replan_reason = evaluation.reason
        logger.warning("Task '%s' not complete: %s. Attempting replan.", state.task_id, replan_reason)
        new_plan = self.planner.replan(state, replan_reason)

        if new_plan.steps:
            state.remaining_steps = list(new_plan.steps)
            state.status = TaskStatus.RECOVERING
            state.metadata["replanned"] = True
        else:
            state.status = TaskStatus.FAILED
            state.metadata["failure_reason"] = replan_reason

        return state

    def _initialize_task(
        self,
        goal: str,
        initial_artifacts: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
    ) -> TaskState:
        """Create a fresh TaskState."""
        state = TaskState(
            goal=goal,
            status=TaskStatus.PENDING,
            artifacts=dict(initial_artifacts or {}),
            metadata=dict(metadata or {}),
        )
        if hasattr(self.recovery_manager, "reset"):
            self.recovery_manager.reset()
        self._last_verification = None
        return state

    def _finalize_task(self, state: TaskState) -> None:
        """Post-execution hook: record outcome into ExperiencePlugin if available."""
        if self.experience_plugin is not None:
            try:
                self.experience_plugin.record_task_state(
                    state=state,
                    verification=self._last_verification,
                )
                logger.info("Recorded experience for task '%s' (status: %s)", state.task_id, state.status.value)
            except Exception as err:
                logger.warning("Failed to record experience for task '%s': %s", state.task_id, err)

        evaluator: Optional[Evaluator] = None,
        plugin_manager: Optional[PluginManager] = None,
        max_steps: int = 15,
    ) -> None:
        self.browser = browser_adapter
        self.permissions = permission_manager or PermissionManager()
        self.plugins = plugin_manager
        self.planner = planner or Planner()
        self.executor = executor or Executor(
            browser_adapter=self.browser,
            permission_manager=self.permissions,
            plugin_manager=self.plugins,
        )
        self.observer = observer or Observer(browser_adapter=self.browser)
        self.recovery = recovery_manager or RecoveryManager()
        self.evaluator = evaluator or Evaluator(max_steps=max_steps)
        self.max_steps = max_steps

    def set_browser_adapter(self, adapter: BaseBrowserAdapter) -> None:
        """Switch active browser adapter (e.g. from Mock to Playwright)."""
        self.browser = adapter
        self.executor.set_browser_adapter(adapter)
        self.observer.set_browser_adapter(adapter)

    async def astep(self, state: AgentState) -> Tuple[AgentState, bool]:
        """Execute a single cycle: plan -> check permissions -> execute -> recover -> observe -> evaluate."""
        # 1. Evaluate termination
        evaluation = self.evaluator.evaluate(state)
        if evaluation.is_complete:
            state.status = AgentStatus.COMPLETED if evaluation.success else AgentStatus.FAILED
            state.metadata["completion_reason"] = evaluation.reason
            return state, True

        # 2. Get next planned action
        action = self.planner.next_action(state)
        if action is None:
            # Plan exhausted
            state.status = AgentStatus.COMPLETED
            return state, True

        logger.info("Executing step %d: %s (%s)", state.step_count + 1, action.action_type, action.description)

        # 3. Execute action
        state.status = AgentStatus.EXECUTING
        result = await self.executor.aexecute(action)

        # 4. Handle recovery if action failed
        if not result.success:
            state.status = AgentStatus.RECOVERING
            strategy = self.recovery.determine_strategy(action, result)
            logger.warning("Action %s failed (%s). Recovery strategy: %s", action.action_type, result.error, strategy.value)

            if strategy == RecoveryStrategy.REPLAN:
                self.planner.replan(state, failure_reason=result.error or "Action failed")
            elif strategy in {RecoveryStrategy.RETRY, RecoveryStrategy.REFRESH_PAGE, RecoveryStrategy.ALTERNATIVE_SELECTOR}:
                rec_action = self.recovery.generate_recovery_action(action, strategy, result)
                if rec_action:
                    logger.info("Executing recovery action: %s", rec_action.action_type)
                    rec_result = await self.executor.aexecute(rec_action)
                    self.observer.update_state(state, rec_action, rec_result)
                    if rec_result.success:
                        result = rec_result

        # 5. Observe and update state
        self.observer.update_state(state, action, result)

        # 6. Re-evaluate post step
        post_eval = self.evaluator.evaluate(state)
        if post_eval.is_complete:
            state.status = AgentStatus.COMPLETED if post_eval.success else AgentStatus.FAILED
            state.metadata["completion_reason"] = post_eval.reason
            return state, True

        state.status = AgentStatus.PLANNING
        return state, False

    def step(self, state: AgentState) -> Tuple[AgentState, bool]:
        """Synchronous wrapper for a single step execution."""
        return asyncio.run(self.astep(state))

    async def arun(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None,
    ) -> AgentState:
        """Run autonomous agent loop until task completion or maximum step limit."""
        steps_limit = max_steps or self.max_steps
        state = AgentState(
            task=task,
            memory=dict(context or {}),
            status=AgentStatus.INITIALIZING,
        )

        try:
            # Initialize browser session if not already initialized
            await self.browser.ainitialize()

            # Generate initial plan
            state.plan = self.planner.create_plan(task, context)
            state.status = AgentStatus.PLANNING

            for _ in range(steps_limit):
                state, is_terminal = await self.astep(state)
                if is_terminal:
                    break

            if state.status not in {AgentStatus.COMPLETED, AgentStatus.FAILED}:
                state.status = AgentStatus.FAILED
                state.metadata["completion_reason"] = f"Reached maximum execution steps ({steps_limit})"

            return state

        finally:
            self.recovery.reset()

    def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None,
    ) -> AgentState:
        """Synchronous wrapper for agent execution."""
        return asyncio.run(self.arun(task, context, max_steps))

    async def aclose(self) -> None:
        """Clean up all browser session resources."""
        await self.browser.aclose()

    def close(self) -> None:
        """Synchronous wrapper for close."""
        self.browser.close()
 main


__all__ = ["AgentController"]
