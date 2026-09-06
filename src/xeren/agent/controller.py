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
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.agent.controller")


class AgentController:
    """Central orchestrator driving autonomous goal execution loops."""

    def __init__(
        self,
        browser_adapter: BaseBrowserAdapter,
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        observer: Optional[Observer] = None,
        recovery_manager: Optional[RecoveryManager] = None,
        permission_manager: Optional[PermissionManager] = None,
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


__all__ = ["AgentController"]
