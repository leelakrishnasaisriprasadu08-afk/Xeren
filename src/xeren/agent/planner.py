"""Planner responsible for task decomposition, step generation, and plan adaptation."""

import logging
from typing import Any, Dict, List, Optional
import uuid

from xeren.agent.types import ActionCategory, AgentAction, AgentState
from xeren.models.base import BaseLLM

logger = logging.getLogger("xeren.agent.planner")


class Planner:
    """Generates and updates structured step plans and produces next executable actions."""

    def __init__(self, llm: Optional[BaseLLM] = None) -> None:
        self.llm = llm

    def create_plan(self, task: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Decompose a user task into an ordered sequence of plan steps."""
        ctx = context or {}
        task_lower = task.lower()

        # Rule-based fast decomposition if no LLM or standard task pattern
        if "browse" in task_lower or "navigate" in task_lower or "website" in task_lower or "page" in task_lower:
            target_url = ctx.get("url", "https://example.com")
            return [
                f"Navigate to {target_url}",
                "Observe page content and interactive elements",
                "Extract requested information",
                "Verify task completion",
            ]

        if "download" in task_lower:
            return [
                "Navigate to download page",
                "Locate download button or link",
                "Download file to approved directory",
                "Verify downloaded file exists",
            ]

        if "upload" in task_lower:
            return [
                "Navigate to upload page",
                "Locate file input element",
                "Upload file from approved directory",
                "Submit form and verify confirmation",
            ]

        return [
            f"Analyze task: {task}",
            "Perform required actions",
            "Verify outcome",
        ]

    def next_action(self, state: AgentState) -> Optional[AgentAction]:
        """Determine next AgentAction to execute based on active state and plan progression."""
        if not state.plan:
            state.plan = self.create_plan(state.task, state.memory)

        if state.step_count >= len(state.plan):
            return None  # All steps executed

        current_step = state.plan[state.step_count]
        state.current_step = current_step
        step_lower = current_step.lower()

        if "navigate to" in step_lower:
            idx = step_lower.find("navigate to")
            url_part = current_step[idx + len("navigate to"):].strip()
            url = url_part if "://" in url_part else f"https://{url_part}"
            return AgentAction(
                action_id=str(uuid.uuid4()),
                action_type="navigate",
                target=url,
                description=current_step,
                category=ActionCategory.INTERACTIVE,
            )

        if "observe" in step_lower:
            return AgentAction(
                action_id=str(uuid.uuid4()),
                action_type="observe",
                description=current_step,
                category=ActionCategory.READ_ONLY,
            )

        if "extract" in step_lower:
            return AgentAction(
                action_id=str(uuid.uuid4()),
                action_type="extract",
                parameters={"extract_type": "text"},
                description=current_step,
                category=ActionCategory.READ_ONLY,
            )

        if "download" in step_lower:
            return AgentAction(
                action_id=str(uuid.uuid4()),
                action_type="download",
                target=state.memory.get("download_selector", "#download-report"),
                parameters={"trigger_selector": state.memory.get("download_selector", "#download-report")},
                consequential=True,
                description=current_step,
                category=ActionCategory.CONSEQUENTIAL,
            )

        if "upload" in step_lower:
            return AgentAction(
                action_id=str(uuid.uuid4()),
                action_type="upload",
                target=state.memory.get("upload_selector", "input[type='file']"),
                parameters={"file_path": state.memory.get("upload_file_path", "")},
                consequential=True,
                description=current_step,
                category=ActionCategory.CONSEQUENTIAL,
            )

        # Fallback generic action
        return AgentAction(
            action_id=str(uuid.uuid4()),
            action_type="observe",
            description=f"Observe progress on: {current_step}",
            category=ActionCategory.READ_ONLY,
        )

    def replan(self, state: AgentState, failure_reason: str) -> List[str]:
        """Revise active plan in response to a failed step or unexpected state."""
        logger.info("Replanning due to failure: %s", failure_reason)
        revised_steps: List[str] = []

        # Keep completed steps
        for i in range(min(state.step_count, len(state.plan))):
            revised_steps.append(state.plan[i])

        # Inject diagnostic and recovery steps
        revised_steps.append("Observe current page state after failure")
        revised_steps.append("Retry action with updated target selector")
        revised_steps.append("Verify final outcome")

        state.plan = revised_steps
        return state.plan


__all__ = ["Planner"]
