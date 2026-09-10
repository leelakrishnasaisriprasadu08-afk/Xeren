"""AgentController: The central autonomous work agent runtime coordinator."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from xeren.agent.actions import Action, ActionResult, ActionType, PermissionLevel
from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.evaluator import DefaultCompletionEvaluator, Evaluator
from xeren.agent.executor import AgentExecutor, Executor
from xeren.agent.interfaces import (
    CompletionEvaluator,
    RecoveryDecision,
)
from xeren.agent.observer import DefaultObserver, Observer
from xeren.agent.permissions import DefaultPermissionManager, PermissionManager
from xeren.agent.planner import MockPlanner, Planner
from xeren.agent.plugins.experience import ExperiencePlugin
from xeren.agent.plugins.verification import VerificationPlugin
from xeren.agent.recovery import DefaultRecoveryManager, RecoveryManager, RecoveryStrategy
from xeren.agent.state import TaskState, TaskStatus
from xeren.agent.types import ActionCategory, AgentAction, AgentState, AgentStatus
from xeren.data.schema import VerificationDetails
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.agent.controller")


class AgentController:
    """Central orchestrator driving autonomous goal execution loops.

    Coordinates the autonomous execution loop:
    PLAN -> SELECT ACTION -> PERMISSION CHECK -> EXECUTE -> OBSERVE -> EVALUATE -> CONTINUE / RETRY / REPLAN / COMPLETE / STOP.
    Supports both TaskState planner execution and AgentState browser loop workflows.
    """

    def __init__(
        self,
        browser_adapter: Optional[BaseBrowserAdapter] = None,
        planner: Optional[Any] = None,
        executor: Optional[Any] = None,
        observer: Optional[Any] = None,
        recovery_manager: Optional[Any] = None,
        permission_manager: Optional[Any] = None,
        completion_evaluator: Optional[CompletionEvaluator] = None,
        plugin_manager: Optional[PluginManager] = None,
        verification_plugin: Optional[VerificationPlugin] = None,
        experience_plugin: Optional[ExperiencePlugin] = None,
        workspace_manager: Optional[Any] = None,
        max_total_cycles: int = 50,
        timeout_seconds: Optional[float] = None,
        max_steps: Optional[int] = None,
    ) -> None:
        if max_steps is not None:
            max_total_cycles = max_steps
        self.browser_adapter = browser_adapter
        self.browser = browser_adapter
        self.plugin_manager = plugin_manager if plugin_manager is not None else PluginManager()
        self.plugins = self.plugin_manager
        self.workspace_manager = workspace_manager

        if browser_adapter is not None:
            self.planner = planner if planner is not None else Planner()
            self.permission_manager = permission_manager if permission_manager is not None else PermissionManager()
            self.executor = executor if executor is not None else Executor(
                browser_adapter=self.browser_adapter,
                permission_manager=self.permission_manager,
                plugin_manager=self.plugin_manager,
            )
            self.observer = observer if observer is not None else Observer(browser_adapter=self.browser_adapter)
            self.recovery_manager = recovery_manager if recovery_manager is not None else RecoveryManager()
        else:
            self.planner = planner if planner is not None else MockPlanner()
            self.permission_manager = permission_manager if permission_manager is not None else DefaultPermissionManager()
            self.executor = executor if executor is not None else AgentExecutor(
                self.plugin_manager,
                workspace_manager=workspace_manager,
                browser_adapter=self.browser_adapter,
            )
            self.observer = observer if observer is not None else DefaultObserver()
            self.recovery_manager = recovery_manager if recovery_manager is not None else DefaultRecoveryManager(max_total_cycles=max_total_cycles)

        self.permissions = self.permission_manager
        self.recovery = self.recovery_manager
        self.completion_evaluator = completion_evaluator if completion_evaluator is not None else DefaultCompletionEvaluator()
        self.evaluator = self.completion_evaluator
        self.max_steps = max_total_cycles

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
        goal: Optional[str] = None,
        initial_artifacts: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        task: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None,
    ) -> Any:
        """Synchronously execute an autonomous task from goal to completion."""
        effective_goal = goal or task or ""
        effective_metadata = dict(metadata or context or {})
        effective_max_steps = max_steps or self.max_steps or self.max_total_cycles

        if self.browser is not None or "task_plan" in effective_metadata or effective_metadata.get("use_agent_state"):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        return pool.submit(
                            asyncio.run,
                            self.arun(
                                goal=goal,
                                initial_artifacts=initial_artifacts,
                                metadata=metadata,
                                timeout=timeout,
                                task=task,
                                context=context,
                                max_steps=max_steps,
                            ),
                        ).result()
                return loop.run_until_complete(
                    self.arun(
                        goal=goal,
                        initial_artifacts=initial_artifacts,
                        metadata=metadata,
                        timeout=timeout,
                        task=task,
                        context=context,
                        max_steps=max_steps,
                    )
                )
            except RuntimeError:
                return asyncio.run(
                    self.arun(
                        goal=goal,
                        initial_artifacts=initial_artifacts,
                        metadata=metadata,
                        timeout=timeout,
                        task=task,
                        context=context,
                        max_steps=max_steps,
                    )
                )

        return self._run_task_state(
            goal=effective_goal,
            initial_artifacts=initial_artifacts,
            metadata=effective_metadata,
            timeout=timeout,
            max_steps=effective_max_steps,
        )

    def _run_task_state(
        self,
        goal: str,
        initial_artifacts: Optional[Dict[str, Any]],
        metadata: Dict[str, Any],
        timeout: Optional[float],
        max_steps: int,
    ) -> TaskState:
        """Execute synchronous TaskState planner loop."""
        start_time = time.perf_counter()
        effective_timeout = timeout or self.timeout_seconds

        # 1. PLAN: Initialize TaskState and formulate initial plan
        state = self._initialize_task(goal, initial_artifacts, metadata)
        logger.info("Starting autonomous task '%s' for goal: %s", state.task_id, goal)

        task_plan = metadata.get("task_plan")
        if task_plan is not None and hasattr(task_plan, "steps") and task_plan.steps:
            steps = list(task_plan.steps)
        elif hasattr(self.planner, "create_plan"):
            plan = self.planner.create_plan(goal, context=state.metadata)
            steps = getattr(plan, "steps", plan if isinstance(plan, list) else [])
        elif hasattr(self.planner, "plan"):
            plan = self.planner.plan(goal=goal, context=state.metadata)
            steps = getattr(plan, "steps", plan if isinstance(plan, list) else [])
        elif callable(self.planner):
            plan = self.planner(goal)
            steps = getattr(plan, "steps", plan if isinstance(plan, list) else [])
        else:
            steps = []

        state.remaining_steps = [self._normalize_action(s) for s in steps]
        state.status = TaskStatus.RUNNING
        state.metadata["plan_id"] = getattr(task_plan, "plan_id", getattr(state, "task_id", str(uuid.uuid4())))

        # 2. LOOP: Execute steps until terminal status reached
        while not state.is_terminal:
            if self._cancelled:
                state.status = TaskStatus.CANCELLED
                state.metadata["cancellation_reason"] = "Task was explicitly cancelled by user/system"
                break

            elapsed = time.perf_counter() - start_time
            if effective_timeout is not None and elapsed > effective_timeout:
                logger.warning("Task '%s' timed out after %.2fs", state.task_id, elapsed)
                state.status = TaskStatus.TIMED_OUT
                state.metadata["timeout_seconds"] = effective_timeout
                break

            cycles_limit = max_steps or self.max_total_cycles
            if state.attempt_count >= cycles_limit:
                logger.error("Task '%s' reached cycle limit (%d). Terminating safely.", state.task_id, cycles_limit)
                state.status = TaskStatus.FAILED
                state.metadata["failure_reason"] = f"Max execution cycles ({cycles_limit}) exceeded"
                break

            state = self.step(state)

            if state.status == TaskStatus.WAITING_APPROVAL:
                logger.info("Task '%s' paused awaiting approval.", state.task_id)
                break

        # 3. Post-execution finalization
        self._finalize_task(state)
        return state

    async def arun(
        self,
        goal: Optional[str] = None,
        initial_artifacts: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        task: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None,
    ) -> Any:
        """Asynchronously execute an autonomous task from goal to completion."""
        effective_goal = goal or task or ""
        effective_metadata = dict(metadata or context or {})
        effective_max_steps = max_steps or self.max_steps or self.max_total_cycles

        if self.browser is not None or "task_plan" in effective_metadata or effective_metadata.get("use_agent_state"):
            return await self._arun_agent_state(
                goal=effective_goal,
                context=effective_metadata,
                max_steps=effective_max_steps,
            )

        return await self._arun_task_state(
            goal=effective_goal,
            initial_artifacts=initial_artifacts,
            metadata=effective_metadata,
            timeout=timeout,
            max_steps=effective_max_steps,
        )

    async def _arun_task_state(
        self,
        goal: str,
        initial_artifacts: Optional[Dict[str, Any]],
        metadata: Dict[str, Any],
        timeout: Optional[float],
        max_steps: int,
    ) -> TaskState:
        """Execute asynchronous TaskState planner loop."""
        start_time = time.perf_counter()
        effective_timeout = timeout or self.timeout_seconds

        state = self._initialize_task(goal, initial_artifacts, metadata)
        logger.info("Starting async autonomous task '%s' for goal: %s", state.task_id, goal)

        task_plan = metadata.get("task_plan")
        if task_plan is not None and hasattr(task_plan, "steps") and task_plan.steps:
            steps = list(task_plan.steps)
        elif hasattr(self.planner, "aplan") and asyncio.iscoroutinefunction(self.planner.aplan):
            plan = await self.planner.aplan(goal=goal, context=state.metadata)
            steps = getattr(plan, "steps", plan if isinstance(plan, list) else [])
        elif hasattr(self.planner, "create_plan"):
            plan = self.planner.create_plan(goal, context=state.metadata)
            steps = getattr(plan, "steps", plan if isinstance(plan, list) else [])
        elif hasattr(self.planner, "plan"):
            plan = self.planner.plan(goal=goal, context=state.metadata)
            steps = getattr(plan, "steps", plan if isinstance(plan, list) else [])
        elif callable(self.planner):
            plan = self.planner(goal)
            steps = getattr(plan, "steps", plan if isinstance(plan, list) else [])
        else:
            steps = []

        state.remaining_steps = [self._normalize_action(s) for s in steps]
        state.status = TaskStatus.RUNNING
        state.metadata["plan_id"] = getattr(task_plan, "plan_id", getattr(state, "task_id", str(uuid.uuid4())))

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

            cycles_limit = max_steps or self.max_total_cycles
            if state.attempt_count >= cycles_limit:
                state.status = TaskStatus.FAILED
                state.metadata["failure_reason"] = f"Max execution cycles ({cycles_limit}) exceeded"
                break

            state = await self.astep(state)

            if state.status == TaskStatus.WAITING_APPROVAL:
                break

        self._finalize_task(state)
        return state

    async def _arun_agent_state(
        self,
        goal: str,
        context: Dict[str, Any],
        max_steps: int,
    ) -> AgentState:
        """Execute autonomous AgentState browser loop."""
        task_plan = context.get("task_plan")

        state = AgentState(
            task=goal,
            status=AgentStatus.PLANNING,
            task_plan=task_plan,
            metadata=context,
            memory=dict(context),
        )

        limit = max_steps or self.max_total_cycles

        # Populate plan steps
        if task_plan is not None and hasattr(task_plan, "steps") and task_plan.steps:
            state.plan = [
                getattr(s, "description", None) or getattr(s, "target", "") or getattr(s, "action_type", "action")
                for s in task_plan.steps
            ]
        elif hasattr(self.planner, "create_plan"):
            plan_res = self.planner.create_plan(goal, context=state.memory)
            if hasattr(plan_res, "steps"):
                state.plan = [
                    getattr(s, "description", None) or getattr(s, "target", "") or getattr(s, "action_type", "action")
                    for s in plan_res.steps
                ]
            elif isinstance(plan_res, list):
                state.plan = [str(s) for s in plan_res]

        state.status = AgentStatus.EXECUTING

        if hasattr(self.observer, "aobserve") and self.browser is not None:
            try:
                obs = await self.observer.aobserve()
                state.last_observation = obs
            except Exception:
                pass

        step_idx = 0
        while not self._cancelled and step_idx < limit:
            action: Optional[AgentAction] = None

            if task_plan is not None and hasattr(task_plan, "steps") and step_idx < len(task_plan.steps):
                p_step = task_plan.steps[step_idx]
                action_type = getattr(p_step, "action_type", "navigate")
                target = getattr(p_step, "target", None)
                params = dict(getattr(p_step, "parameters", {}) or {})
                cat = getattr(p_step, "category", ActionCategory.INTERACTIVE)
                consequential = getattr(p_step, "consequential", False)
                action = AgentAction(
                    action_id=getattr(p_step, "step_id", getattr(p_step, "action_id", str(uuid.uuid4()))),
                    action_type=action_type,
                    target=target,
                    parameters=params,
                    category=cat,
                    consequential=consequential,
                    description=getattr(p_step, "description", None),
                )
            elif hasattr(self.planner, "next_action"):
                action = self.planner.next_action(state)

            if action is None:
                state.status = AgentStatus.COMPLETED
                break

            state.current_step = action.description or action.action_type

            # Execute action
            result = await self.executor.aexecute(action)

            # Observe & update state
            if hasattr(self.observer, "update_state"):
                self.observer.update_state(state, action, result)
            else:
                state.history.append((action, result))
                if result.success:
                    state.step_count += 1

            step_idx += 1

            if not result.success:
                if not getattr(result, "recoverable", True) or result.error_code == "PERMISSION_DENIED":
                    state.status = AgentStatus.FAILED
                    state.metadata["completion_reason"] = result.error or "Permission denied or unrecoverable error"
                    break

                # Recovery attempt if steps remain
                if hasattr(self.recovery_manager, "determine_strategy") and step_idx < limit:
                    strat = self.recovery_manager.determine_strategy(action, result)
                    if hasattr(self.recovery_manager, "generate_recovery_action"):
                        rec_action = self.recovery_manager.generate_recovery_action(action, strat, result)
                        if rec_action and step_idx < limit:
                            rec_res = await self.executor.aexecute(rec_action)
                            if hasattr(self.observer, "update_state"):
                                self.observer.update_state(state, rec_action, rec_res)
                            else:
                                state.history.append((rec_action, rec_res))
                                if rec_res.success:
                                    state.step_count += 1
                            step_idx += 1
                break

            if state.plan and state.step_count >= len(state.plan):
                state.status = AgentStatus.COMPLETED
                break

        if not self._cancelled and state.status == AgentStatus.EXECUTING:
            if state.history and all(res.success for _, res in state.history):
                state.status = AgentStatus.COMPLETED
            elif state.history and any(not res.success for _, res in state.history):
                state.status = AgentStatus.FAILED
            else:
                state.status = AgentStatus.COMPLETED

        return state

    def _normalize_action(self, raw_action: Any) -> Action:
        """Convert a raw action string or step object into a standardized Action."""
        if isinstance(raw_action, Action):
            return raw_action

        if isinstance(raw_action, str):
            raw_lower = raw_action.lower()
            if any(w in raw_lower for w in ["powershell", "cmd", "run", "launch", "open", "desktop", "os"]):
                target = "automation"
                params = {"command": raw_action}
            elif any(w in raw_lower for w in ["research", "search", "google", "browse"]):
                target = "research"
                params = {"query": raw_action, "depth": "standard"}
            elif any(w in raw_lower for w in ["knowledge", "rag", "document", "question", "explain", "what is"]):
                target = "knowledge"
                params = {"query": raw_action, "operation": "query"}
            elif any(w in raw_lower for w in ["website", "html", "css", "web page"]):
                target = "website"
                params = {"task": raw_action, "prompt": raw_action}
            elif any(w in raw_lower for w in ["file", "read file", "write file"]):
                target = "file"
                params = {"operation": "read", "path": raw_action}
            elif any(w in raw_lower for w in ["data", "csv", "json", "pandas"]):
                target = "data"
                params = {"operation": "summary", "data": raw_action}
            else:
                target = "coding"
                params = {"task": raw_action, "source_code": "", "command": raw_action}

            return Action(
                action_id=str(uuid.uuid4()),
                action_type=ActionType.PLUGIN.value,
                target=target,
                parameters=params,
                description=raw_action,
            )

        raw_plugin = getattr(raw_action, "plugin_name", None)
        raw_target = getattr(raw_action, "target", None)
        raw_type = getattr(raw_action, "action_type", None)

        type_str = str(getattr(raw_type, "value", raw_type) or "").lower()
        target_str = str(getattr(raw_target, "value", raw_target) or "").lower()

        if (
            type_str in {"navigate", "click", "type", "select", "scroll", "extract", "upload", "download", "close", "observe"}
            or target_str.startswith("http://")
            or target_str.startswith("https://")
        ):
            target = "browser"
        elif raw_plugin:
            target = str(getattr(raw_plugin, "value", raw_plugin)).lower()
        elif raw_target:
            target = target_str
        elif raw_type:
            target = type_str
        else:
            target = "automation"

        if target in ("desktop", "os"):
            target = "automation"

        action_type = raw_type or ActionType.PLUGIN.value
        if hasattr(action_type, "value"):
            action_type = action_type.value
        action_type = str(action_type)

        params = dict(getattr(raw_action, "parameters", {}) or {})
        desc = getattr(raw_action, "description", str(raw_action))
        step_id = getattr(raw_action, "step_id", getattr(raw_action, "action_id", str(uuid.uuid4())))
        consequential = bool(getattr(raw_action, "consequential", False))

        if target == "coding":
            if "task" not in params and "source_code" not in params:
                params["task"] = desc
        elif target == "knowledge":
            if "query" not in params:
                params["query"] = desc
            if "operation" not in params:
                params["operation"] = "query"
        elif target == "research":
            if "query" not in params:
                params["query"] = desc
        elif target == "website":
            if "task" not in params and "prompt" not in params:
                params["task"] = desc
        elif target == "automation":
            if "command" not in params:
                params["command"] = desc
        elif target == "browser":
            if "url" not in params:
                if target_str.startswith("http://") or target_str.startswith("https://"):
                    params["url"] = target_str
            if "operation" not in params and "action" not in params:
                params["operation"] = type_str or "navigate"

        return Action(
            action_id=str(step_id),
            action_type=action_type,
            target=target,
            parameters=params,
            description=desc,
            consequential=consequential,
        )

    def step(self, state: TaskState) -> TaskState:
        """Execute a single cycle of the autonomous task loop."""
        if state.is_terminal:
            return state

        if not state.remaining_steps:
            return self._evaluate_and_complete(state)

        # 1. SELECT ACTION
        action = self._normalize_action(state.remaining_steps[0])
        state.remaining_steps[0] = action
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
                    state.metadata["completion_reason"] = f"Permission denied: {auth_err}"
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

        action = self._normalize_action(state.remaining_steps[0])
        state.remaining_steps[0] = action
        state.current_step = action

        permission_level = self.permission_manager.get_permission_level(action)
        action.permission_level = permission_level

        if permission_level == PermissionLevel.REQUIRES_APPROVAL:
            if not self.permission_manager.is_authorized(action, state.metadata):
                approved = self.permission_manager.request_approval(action, state.metadata)
                if not approved:
                    state.status = TaskStatus.WAITING_APPROVAL
                    auth_err = f"Action '{action.action_id}' on '{action.target}' requires approval and is not authorized."
                    state.metadata["completion_reason"] = f"Permission denied: {auth_err}"
                    res = ActionResult(
                        action_id=action.action_id,
                        success=False,
                        error=auth_err,
                        metadata={"target": action.target, "permission_level": permission_level.value},
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
            steps = getattr(new_plan, "steps", new_plan if isinstance(new_plan, list) else [])
            if steps:
                state.remaining_steps = list(steps)
                state.current_step = None
                state.metadata["replanned"] = True
            else:
                state.status = TaskStatus.FAILED
                state.metadata["failure_reason"] = f"Replan returned no alternative steps. Error: {replan_reason}"
            return state

        elif decision == RecoveryDecision.WAIT_APPROVAL:
            state.status = TaskStatus.WAITING_APPROVAL
            return state

        else:
            state.status = TaskStatus.FAILED
            state.metadata["failure_reason"] = result.error or "Execution failed and recovery is impossible"
            return state

    def _evaluate_and_complete(self, state: TaskState) -> TaskState:
        """Run verification gate and evaluate if task requirements have been satisfied."""
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

        evaluation = self.completion_evaluator.evaluate(state, verif_result)
        state.metadata["completion_evaluation"] = evaluation.model_dump()

        if evaluation.is_complete:
            state.status = TaskStatus.COMPLETED
            logger.info("Task '%s' successfully COMPLETED!", state.task_id)
            return state

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

    def set_browser_adapter(self, adapter: Optional[BaseBrowserAdapter]) -> None:
        """Switch active browser adapter (e.g. from Mock to Playwright)."""
        self.browser_adapter = adapter
        self.browser = adapter
        if adapter is not None:
            if hasattr(self.executor, "set_browser_adapter"):
                self.executor.set_browser_adapter(adapter)
            elif hasattr(self.executor, "browser"):
                self.executor.browser = adapter
            if hasattr(self.observer, "set_browser_adapter"):
                self.observer.set_browser_adapter(adapter)
            elif hasattr(self.observer, "browser"):
                self.observer.browser = adapter

    async def aclose(self) -> None:
        """Clean up all browser session resources."""
        if self.browser and hasattr(self.browser, "aclose"):
            await self.browser.aclose()

    def close(self) -> None:
        """Synchronous wrapper for close."""
        if self.browser and hasattr(self.browser, "close"):
            self.browser.close()


__all__ = ["AgentController"]
