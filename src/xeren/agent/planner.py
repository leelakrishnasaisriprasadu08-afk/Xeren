"""Planner implementations and Core adapter for the Autonomous Work Agent."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import logging
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field

from xeren.agent.actions import Action, ActionType, PermissionLevel
from xeren.agent.interfaces import Planner
from xeren.agent.state import TaskState
from xeren.agent.validator import PlanValidationError, PlanValidationResult, PlanValidator

if TYPE_CHECKING:
    from xeren.models.base import BaseLLM
    from xeren.plugins.manager import PluginManager

"""Planner responsible for task decomposition, step generation, and plan adaptation."""

import logging
from typing import Any, Dict, List, Optional
import uuid

from xeren.agent.types import ActionCategory, AgentAction, AgentState
from xeren.models.base import BaseLLM
 main

logger = logging.getLogger("xeren.agent.planner")


 feature/core-architecture
class TaskPlan(BaseModel):
    """A sequence of planned actions generated for a task goal."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the plan",
    )
    goal: str = Field(
        ...,
        description="Goal for which this plan was formulated",
    )
    steps: List[Action] = Field(
        default_factory=list,
        description="Chronological sequence of actions to be executed",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Planner metadata and rationale",
    )

    model_config = {"arbitrary_types_allowed": True}


class MockPlanner(Planner):
    """Deterministic, mock-first planner for offline operation and testing.

    Can be injected with canned plans, rule-based generators, or custom callbacks.
    """

    def __init__(
        self,
        default_steps: Optional[List[Action]] = None,
        goal_plans: Optional[Dict[str, List[Action]]] = None,
        replan_steps: Optional[List[Action]] = None,
        plan_fn: Optional[Callable[[str, Optional[Dict[str, Any]]], List[Action]]] = None,
        replan_fn: Optional[Callable[[TaskState, str], List[Action]]] = None,
    ) -> None:
        self.default_steps = default_steps or []
        self._goal_plans = {k.lower(): v for k, v in (goal_plans or {}).items()}
        self._replan_steps = replan_steps
        self._plan_fn = plan_fn
        self._replan_fn = replan_fn
        self.plan_call_count = 0
        self.replan_call_count = 0

    def set_plan_for_goal(self, goal: str, steps: List[Action]) -> None:
        """Register a canned plan for a specific goal."""
        self._goal_plans[goal.lower()] = steps

    def set_default_steps(self, steps: List[Action]) -> None:
        """Set fallback default steps when no specific goal matches."""
        self.default_steps = steps

    def set_replan_steps(self, steps: List[Action]) -> None:
        """Set canned steps to return when replanning."""
        self._replan_steps = steps

    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """Generate a deterministic plan for the goal."""
        self.plan_call_count += 1

        if self._plan_fn is not None:
            steps = self._plan_fn(goal, context)
            return TaskPlan(goal=goal, steps=steps, metadata={"source": "plan_fn"})

        goal_key = goal.strip().lower()
        for registered_key, steps in self._goal_plans.items():
            if registered_key in goal_key or goal_key in registered_key:
                return TaskPlan(
                    goal=goal,
                    steps=[s.model_copy(deep=True) for s in steps],
                    metadata={"source": "canned_goal_match"},
                )

        if self.default_steps:
            return TaskPlan(
                goal=goal,
                steps=[s.model_copy(deep=True) for s in self.default_steps],
                metadata={"source": "default_steps"},
            )

        # Rule-based fallback if no steps configured
        inferred_steps: List[Action] = []
        if "workspace" in goal_key or (("find" in goal_key or "discover" in goal_key) and any(k in goal_key for k in ("file", "project", "data", "doc", "bug", "yesterday"))):
            inferred_steps.append(
                Action(
                    target="workspace",
                    parameters={"operation": "discover", "goal": goal},
                    description=f"Discover workspace resources for: {goal}",
                )
            )
        if "research" in goal_key:
            inferred_steps.append(
                Action(
                    target="research",
                    parameters={"query": goal},
                    description=f"Research: {goal}",
                )
            )
        if "code" in goal_key or "coding" in goal_key:
            inferred_steps.append(
                Action(
                    target="coding",
                    parameters={"operation": "generate", "task": goal},
                    description=f"Generate code for: {goal}",
                )
            )
        if "website" in goal_key:
            inferred_steps.append(
                Action(
                    target="website",
                    parameters={"operation": "generate", "specification": {"title": goal}},
                    description=f"Generate website for: {goal}",
                )
            )
        if "data" in goal_key:
            inferred_steps.append(
                Action(
                    target="data",
                    parameters={"operation": "inspect", "dataset": goal},
                    description=f"Inspect data for: {goal}",
                )
            )
        if "browse" in goal_key or "browser" in goal_key or "http" in goal_key:
            inferred_steps.append(
                Action(
                    action_type=ActionType.BROWSER.value,
                    target="browser",
                    parameters={"action": "navigate", "url": "https://example.org"},
                    description="Navigate to website",
                )
            )

        if not inferred_steps:
            inferred_steps.append(
                Action(
                    target="research",
                    parameters={"query": goal},
                    description=f"Execute task: {goal}",
                )
            )

        return TaskPlan(
            goal=goal,
            steps=inferred_steps,
            metadata={"source": "rule_inferred"},
        )

    def replan(self, state: TaskState, failure_reason: str) -> TaskPlan:
        """Generate a recovered plan following a failure."""
        self.replan_call_count += 1

        if self._replan_fn is not None:
            steps = self._replan_fn(state, failure_reason)
            return TaskPlan(
                goal=state.goal,
                steps=steps,
                metadata={"source": "replan_fn", "failure_reason": failure_reason},
            )

        if self._replan_steps is not None:
            return TaskPlan(
                goal=state.goal,
                steps=[s.model_copy(deep=True) for s in self._replan_steps],
                metadata={"source": "canned_replan", "failure_reason": failure_reason},
            )

        # Generate a recovery action or modified remaining steps
        remaining = [s.model_copy(deep=True) for s in state.remaining_steps]
        if remaining:
            # Modify first remaining action parameters to mitigate failure
            first = remaining[0]
            first.parameters["retry_context"] = failure_reason
            first.metadata["replanned"] = True
            return TaskPlan(
                goal=state.goal,
                steps=remaining,
                metadata={"source": "modified_remaining", "failure_reason": failure_reason},
            )

        # Fallback alternative recovery action
        recovery_step = Action(
            target="research",
            parameters={"query": f"Alternative solution for {state.goal} after failure: {failure_reason}"},
            description="Fallback research for alternative path",
            metadata={"is_recovery": True},
        )
        return TaskPlan(
            goal=state.goal,
            steps=[recovery_step],
            metadata={"source": "fallback_recovery", "failure_reason": failure_reason},
        )


class CorePlannerAdapter(Planner):
    """Adapter allowing XerenCore (or any injected model provider) to serve as the Planner.

    Establishes a clean, secure integration boundary:
    XerenCore / Model Provider -> Plan Generation -> CoT Sanitization -> PlanValidator -> Validated TaskPlan -> AgentController.
    """

    def __init__(
        self,
        core: Optional[Any] = None,
        model_provider: Optional[Any] = None,
        plugin_manager: Optional[PluginManager] = None,
        validator: Optional[PlanValidator] = None,
        timeout_seconds: Optional[float] = 30.0,
        max_steps: int = 20,
        fallback_to_rule_planner: bool = True,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.core = core
        self.model_provider = model_provider
        self.plugin_manager = plugin_manager
        if self.plugin_manager is None and self.core is not None:
            self.plugin_manager = getattr(self.core, "plugin_manager", None)
        self.validator = validator or PlanValidator(max_steps=max_steps)
        self.timeout_seconds = timeout_seconds
        self.max_steps = max_steps
        self.fallback_to_rule_planner = fallback_to_rule_planner
        self.system_prompt = system_prompt or (
            "You are the autonomous planning engine for Xeren. Given a goal and context, "
            "generate a valid TaskPlan conforming to the schema. Output JSON only."
        )

    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """Generate an action plan by querying the injected Core / model provider and validating."""
        logger.info("CorePlannerAdapter generating plan for goal: %s", goal)
        plan_metadata: Dict[str, Any] = {}
        candidate_plan: Optional[TaskPlan] = None

        # 1. Resolve model provider
        provider = self.model_provider
        if provider is None and self.core is not None:
            if hasattr(self.core, "llm"):
                provider = self.core.llm
            elif hasattr(self.core, "plan") and callable(self.core.plan):
                provider = self.core.plan

        # 2. Invoke provider if present
        if provider is not None:
            try:
                candidate_plan = self._invoke_provider(provider, goal, context)
                plan_metadata["provider_type"] = type(provider).__name__
            except Exception as err:
                logger.warning("CorePlannerAdapter provider invocation failed: %s", err)
                if not self.fallback_to_rule_planner:
                    if isinstance(err, PlanValidationError):
                        raise
                    raise PlanValidationError(f"Model provider failure: {err}", errors=[str(err)]) from err
                plan_metadata["provider_failure"] = str(err)

        # 3. Rule-based inference if provider returned None or not provided
        if candidate_plan is None:
            candidate_plan = self._infer_rule_plan(goal, context)
            plan_metadata["source"] = "rule_inferred"

        # 4. Strict validation via PlanValidator
        val_res = self.validator.validate_plan(candidate_plan, self.plugin_manager)
        if not val_res.is_valid:
            logger.warning("CorePlannerAdapter candidate plan failed validation: %s", val_res.errors)
            if self.fallback_to_rule_planner and plan_metadata.get("source") != "rule_inferred":
                fallback_plan = self._infer_rule_plan(goal, context)
                rule_val = self.validator.validate_plan(fallback_plan, self.plugin_manager)
                if rule_val.is_valid and rule_val.sanitized_plan is not None:
                    rule_val.sanitized_plan.metadata.update(plan_metadata)
                    rule_val.sanitized_plan.metadata["original_plan_validation_errors"] = val_res.errors
                    return rule_val.sanitized_plan
            raise PlanValidationError(
                f"Generated plan failed validation: {'; '.join(val_res.errors)}",
                errors=val_res.errors,
            )

        sanitized = val_res.sanitized_plan
        if sanitized is None:
            raise PlanValidationError("Plan validation returned no sanitized plan")

        sanitized.metadata.update(plan_metadata)
        return sanitized

    def replan(self, state: TaskState, failure_reason: str) -> TaskPlan:
        """Generate a recovered plan via the injected model provider or rule engine."""
        logger.info("CorePlannerAdapter replanning after failure: %s", failure_reason)
        provider = self.model_provider
        if provider is None and self.core is not None:
            if hasattr(self.core, "llm"):
                provider = self.core.llm

        if provider is not None and hasattr(provider, "replan") and callable(provider.replan):
            try:
                candidate = provider.replan(state, failure_reason)
                val_res = self.validator.validate_plan(candidate, self.plugin_manager)
                if val_res.is_valid and val_res.sanitized_plan is not None:
                    return val_res.sanitized_plan
            except Exception as err:
                logger.warning("Provider replan failed: %s. Falling back to rule replan.", err)

        available_plugins = self.plugin_manager.list_names() if self.plugin_manager else []
        target = "research" if "research" in available_plugins else ("coding" if "coding" in available_plugins else "research")
        steps = [
            Action(
                target=target,
                parameters={"query": f"Fix or workaround for {state.goal}: {failure_reason}"},
                description=f"Replan recovery: {failure_reason}",
                metadata={"is_recovery": True},
            )
        ]
        replan_plan = TaskPlan(
            goal=state.goal,
            steps=steps,
            metadata={"source": "core_planner_adapter_replan", "failure_reason": failure_reason},
        )
        val_res = self.validator.validate_plan(replan_plan, self.plugin_manager)
        return val_res.sanitized_plan or replan_plan

    def _invoke_provider(self, provider: Any, goal: str, context: Optional[Dict[str, Any]]) -> TaskPlan:
        """Call the provider with timeout boundary and parse output."""
        if self.timeout_seconds is not None and self.timeout_seconds > 0:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._call_provider, provider, goal, context)
                try:
                    raw_result = future.result(timeout=self.timeout_seconds)
                except FuturesTimeoutError as timeout_err:
                    raise TimeoutError(
                        f"Model provider planning timed out after {self.timeout_seconds}s"
                    ) from timeout_err
        else:
            raw_result = self._call_provider(provider, goal, context)

        return self._parse_provider_output(raw_result, goal)

    def _call_provider(self, provider: Any, goal: str, context: Optional[Dict[str, Any]]) -> Any:
        """Invoke various provider types (BaseLLM, callable, or custom object)."""
        if hasattr(provider, "generate") and callable(provider.generate):
            prompt = self._build_planning_prompt(goal, context)
            from xeren.models.types import ChatMessage
            msgs = [
                ChatMessage.system(self.system_prompt),
                ChatMessage.user(prompt),
            ]
            response = provider.generate(msgs)
            return getattr(response, "content", response)

        if callable(provider):
            return provider(goal, context)

        if hasattr(provider, "plan") and callable(provider.plan):
            return provider.plan(goal, context)

        raise TypeError(f"Unsupported model provider type: {type(provider).__name__}")

    def _build_planning_prompt(self, goal: str, context: Optional[Dict[str, Any]]) -> str:
        available = self.plugin_manager.list_names() if self.plugin_manager else []
        return (
            f"Goal: {goal}\n"
            f"Context: {context or {}}\n"
            f"Available plugins: {available}\n\n"
            "Generate a JSON action plan with schema:\n"
            '{\n  "goal": string,\n  "steps": [\n    {\n      "target": string,\n      "action_type": "plugin"|"browser"|"verification"|"system"|"custom",\n      "parameters": object,\n      "description": string,\n      "permission_level": "safe"|"requires_approval"\n    }\n  ]\n}\n'
            "Respond strictly with valid JSON only."
        )

    def _parse_provider_output(self, raw: Any, default_goal: str) -> TaskPlan:
        """Parse raw provider output into candidate TaskPlan."""
        if isinstance(raw, TaskPlan):
            return raw

        if isinstance(raw, dict):
            return TaskPlan.model_validate(raw)

        if isinstance(raw, str):
            text = raw.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            try:
                data = json.loads(text)
            except Exception as json_err:
                raise PlanValidationError(
                    f"Model output is not valid JSON: {text[:100]}...",
                    errors=[str(json_err)],
                ) from json_err

            if not isinstance(data, dict):
                raise PlanValidationError(
                    f"Model output JSON must be an object, got {type(data).__name__}"
                )

            if "goal" not in data:
                data["goal"] = default_goal

            try:
                return TaskPlan.model_validate(data)
            except Exception as val_err:
                raise PlanValidationError(
                    f"Model output JSON does not match TaskPlan schema: {val_err}",
                    errors=[str(val_err)],
                ) from val_err

        raise PlanValidationError(f"Cannot parse provider output of type {type(raw).__name__}")

    def _infer_rule_plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """Fallback rule-based plan inference."""
        available_plugins: List[str] = []
        if self.plugin_manager is not None:
            available_plugins = list(self.plugin_manager.list_names())
        elif self.core is not None and hasattr(self.core, "plugin_manager"):
            pm_obj: Any = getattr(self.core, "plugin_manager", None)
            if pm_obj is not None and hasattr(pm_obj, "list_names"):
                raw_names: Any = pm_obj.list_names()
                if isinstance(raw_names, (list, tuple, set)):
                    available_plugins = [str(name) for name in raw_names]

        steps: List[Action] = []
        goal_lower = goal.lower()

        if "workspace" in goal_lower or (("find" in goal_lower or "discover" in goal_lower) and any(k in goal_lower for k in ("file", "project", "data", "doc", "bug", "yesterday"))):
            steps.append(
                Action(
                    target="workspace",
                    parameters={"operation": "discover", "goal": goal},
                    description=f"Discover workspace resources for: {goal}",
                )
            )

        if "coding" in available_plugins and ("code" in goal_lower or "script" in goal_lower or "python" in goal_lower):
            steps.append(
                Action(
                    target="coding",
                    parameters={"operation": "generate", "task": goal},
                    description=f"Generate code for: {goal}",
                )
            )
        elif "research" in available_plugins and ("research" in goal_lower or "find" in goal_lower or "search" in goal_lower):
            steps.append(
                Action(
                    target="research",
                    parameters={"query": goal},
                    description=f"Research topic: {goal}",
                )
            )
        elif "data" in available_plugins and "data" in goal_lower:
            steps.append(
                Action(
                    target="data",
                    parameters={"operation": "inspect", "dataset": goal},
                    description=f"Inspect data for: {goal}",
                )
            )
        elif "website" in available_plugins and "website" in goal_lower:
            steps.append(
                Action(
                    target="website",
                    parameters={"operation": "generate", "specification": {"title": goal}},
                    description=f"Generate website for: {goal}",
                )
            )
        else:
            first_target = available_plugins[0] if available_plugins else "research"
            steps.append(
                Action(
                    target=first_target,
                    parameters={"query": goal} if first_target == "research" else {"task": goal},
                    description=f"Execute {first_target} action for: {goal}",
                )
            )

        return TaskPlan(
            goal=goal,
            steps=steps,
            metadata={"source": "core_planner_adapter", "available_plugins": available_plugins},
        )


__all__ = [
    "TaskPlan",
    "MockPlanner",
    "CorePlannerAdapter",
]

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
 main
