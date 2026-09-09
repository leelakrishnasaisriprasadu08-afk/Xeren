"""DefaultObserver for collecting perceptions and artifacts post-execution."""

from __future__ import annotations

import logging
from typing import Any, Dict

from xeren.agent.actions import Action, ActionResult
from xeren.agent.interfaces import Observer
from xeren.agent.state import Observation, TaskState

"""Observer capturing environment state and maintaining execution context traces."""

import logging
from typing import Optional, Tuple

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.types import ActionResult, AgentAction, AgentState, BrowserObservation
 main

logger = logging.getLogger("xeren.agent.observer")


 feature/core-architecture
class DefaultObserver(Observer):
    """Observes action results, generates perception summaries, and gathers artifacts."""

    def observe(self, action: Action, result: ActionResult, state: TaskState) -> Observation:
        """Process the outcome of an executed action into a structured Observation."""
        logger.debug("Observing result for action '%s'", action.action_id)

        # 1. Build summary
        if result.success:
            summary = (
                f"Action '{action.action_id}' on '{action.target}' completed successfully "
                f"in {result.latency_ms:.1f}ms."
            )
            if action.description:
                summary += f" ({action.description})"
        else:
            summary = (
                f"Action '{action.action_id}' on '{action.target}' failed: "
                f"{result.error or 'Unknown error'}"
            )

        # 2. Gather artifacts discovered
        artifacts: Dict[str, Any] = dict(result.artifacts)

        # 3. Create observation
        obs = Observation(
            action_id=action.action_id,
            success=result.success,
            summary=summary,
            data=result.output,
            error=result.error,
            artifacts_discovered=artifacts,
            metadata={
                "target": action.target,
                "latency_ms": result.latency_ms,
                "attempt_count": state.attempt_count,
                **result.metadata,
            },
        )

        return obs


__all__ = ["DefaultObserver"]

class Observer:
    """Observes page state via browser adapter and updates AgentState history."""

    def __init__(self, browser_adapter: BaseBrowserAdapter) -> None:
        self.browser = browser_adapter

    def set_browser_adapter(self, adapter: BaseBrowserAdapter) -> None:
        """Switch or update the active browser adapter."""
        self.browser = adapter

    async def aobserve(self) -> BrowserObservation:
        """Capture fresh observation from the active browser page."""
        return await self.browser.aobserve()

    def update_state(
        self,
        state: AgentState,
        action: AgentAction,
        result: ActionResult,
        observation: Optional[BrowserObservation] = None,
    ) -> AgentState:
        """Update agent state with action result, step count, and observation."""
        obs = observation or result.observation
        if obs:
            state.last_observation = obs

        state.history.append((action, result))
        if result.success:
            state.step_count += 1

        # Store useful outcome details in working memory
        if result.success and result.data:
            state.memory[f"step_{state.step_count}_result"] = result.data

        return state


__all__ = ["Observer"]
 main
