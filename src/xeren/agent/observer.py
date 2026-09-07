"""DefaultObserver for collecting perceptions and artifacts post-execution."""

from __future__ import annotations

import logging
from typing import Any, Dict

from xeren.agent.actions import Action, ActionResult
from xeren.agent.interfaces import Observer
from xeren.agent.state import Observation, TaskState

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
