"""Observer capturing environment state and maintaining execution context traces."""

import logging
from typing import Optional, Tuple

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.types import ActionResult, AgentAction, AgentState, BrowserObservation

logger = logging.getLogger("xeren.agent.observer")


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
