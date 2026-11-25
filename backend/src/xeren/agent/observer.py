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

logger = logging.getLogger("xeren.agent.observer")

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
        artifacts: Dict[str, Any] = dict(getattr(result, "artifacts", {}) or {})

        # 3. Create observation
        obs = Observation(
            action_id=getattr(action, "action_id", "unknown"),
            success=getattr(result, "success", True),
            summary=summary,
            data=getattr(result, "output", getattr(result, "data", None)),
            error=getattr(result, "error", None),
            artifacts_discovered=artifacts,
            metadata={
                "target": getattr(action, "target", "unknown"),
                "latency_ms": getattr(result, "latency_ms", 0.0),
                "attempt_count": getattr(state, "attempt_count", getattr(state, "step_count", 0)),
                **getattr(result, "metadata", {}),
            },
        )

        return obs

    def update_state(
        self,
        state: Any,
        action: Any,
        result: Any,
        observation: Optional[Any] = None,
    ) -> Any:
        obs = observation or getattr(result, "observation", None)
        if obs and hasattr(state, "last_observation"):
            state.last_observation = obs

        if hasattr(state, "history") and isinstance(state.history, list):
            state.history.append((action, result))

        if hasattr(state, "step_count"):
            if getattr(result, "success", True):
                state.step_count += 1

        if hasattr(state, "memory") and isinstance(state.memory, dict):
            step_c = getattr(state, "step_count", 1)
            data = getattr(result, "data", None) or getattr(result, "output", None)
            if data:
                state.memory[f"step_{step_c}_result"] = data

        return state

    def set_browser_adapter(self, adapter: Any) -> None:
        self.browser = adapter

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


__all__ = ["DefaultObserver", "Observer"]
