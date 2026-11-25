"""Plan validation engine and safety constraints for agent task plans."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from xeren.agent.actions import Action, ActionType, PermissionLevel
from xeren.plugins.manager import PluginManager

if TYPE_CHECKING:
    from xeren.agent.planner import TaskPlan

logger = logging.getLogger("xeren.agent.validator")

# Known built-in and system targets acceptable for autonomous execution
STANDARD_SYSTEM_TARGETS: Set[str] = {
    "browser",
    "research",
    "coding",
    "website",
    "data",
    "file",
    "workspace",
    "automation",
    "api",
    "conversation",
    "verification",
    "experience",
}

# Consequential keywords that necessitate explicit user authorization
CONSEQUENTIAL_KEYWORDS: List[str] = [
    "delete",
    "remove",
    "rm",
    "drop",
    "truncate",
    "purge",
    "overwrite",
    "destroy",
    "kill",
    "terminate",
    "revoke",
    "shutdown",
]


class PlanValidationError(Exception):
    """Exception raised when a task plan fails security or schema validation."""

    def __init__(self, message: str, errors: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []

    def __str__(self) -> str:
        err_str = "; ".join(self.errors) if self.errors else self.message
        return f"[PlanValidationError] {self.message} (details: {err_str})"


class PlanValidationResult(BaseModel):
    """Diagnostic outcome of plan validation."""

    is_valid: bool = Field(
        ...,
        description="Whether the plan meets all schema, safety, and capability constraints",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation failure errors",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of non-fatal warnings or adjusted permissions",
    )
    sanitized_plan: Optional[Any] = Field(
        default=None,
        description="Sanitized and validated plan instance with CoT stripped",
    )

    model_config = {"arbitrary_types_allowed": True}


class PlanValidator:
    """Validates Core-generated plans before they are allowed to reach the executor."""

    def __init__(
        self,
        max_steps: int = 20,
        allowed_targets: Optional[Set[str]] = None,
        require_plugin_registration: bool = True,
    ) -> None:
        self.max_steps = max_steps
        self.allowed_targets = allowed_targets or set(STANDARD_SYSTEM_TARGETS)
        self.require_plugin_registration = require_plugin_registration

    def validate_plan(
        self,
        plan: Any,
        plugin_manager: Optional[PluginManager] = None,
    ) -> PlanValidationResult:
        """Validate a candidate TaskPlan against schema, capabilities, and safety bounds."""
        from xeren.agent.planner import TaskPlan

        errors: List[str] = []
        warnings: List[str] = []

        # 1. Schema check
        if not isinstance(plan, TaskPlan):
            errors.append(f"Plan must be an instance of TaskPlan, got {type(plan).__name__}")
            return PlanValidationResult(is_valid=False, errors=errors)

        if not plan.goal or not plan.goal.strip():
            errors.append("TaskPlan must have a non-empty 'goal'")

        # 2. Step limits
        if not plan.steps:
            errors.append("TaskPlan contains zero executable steps")

        if len(plan.steps) > self.max_steps:
            errors.append(
                f"TaskPlan exceeds maximum step limit ({len(plan.steps)} > {self.max_steps})"
            )

        # 3. Known plugins and valid targets
        registered_plugins: Set[str] = set()
        if plugin_manager is not None:
            registered_plugins = {name.lower() for name in plugin_manager.list_names()}

        known_targets = self.allowed_targets.union(registered_plugins)

        valid_action_types = {t.value for t in ActionType}

        sanitized_steps: List[Action] = []
        for idx, step in enumerate(plan.steps):
            step_id = f"Step #{idx + 1}"

            # Verify action type
            if not isinstance(step, Action):
                errors.append(f"{step_id} is not an instance of Action")
                continue

            if step.action_type not in valid_action_types:
                errors.append(
                    f"{step_id} has invalid action_type '{step.action_type}'. Must be one of {sorted(valid_action_types)}"
                )

            # Verify target
            target = step.target.strip().lower()
            if not target:
                errors.append(f"{step_id} has an empty 'target'")
            elif self.require_plugin_registration and target not in known_targets:
                errors.append(
                    f"{step_id} targets unknown plugin/tool '{target}'. Known targets: {sorted(known_targets)}"
                )

            # Verify parameters
            if not isinstance(step.parameters, dict):
                errors.append(
                    f"{step_id} parameters must be a dictionary, got {type(step.parameters).__name__}"
                )

            # 4. Consequential operation permission checks
            is_consequential = self._is_consequential_action(step)
            permission_level = step.permission_level
            if is_consequential and permission_level != PermissionLevel.REQUIRES_APPROVAL:
                warnings.append(
                    f"{step_id} ({target}) performs consequential operation and was upgraded to REQUIRES_APPROVAL"
                )
                permission_level = PermissionLevel.REQUIRES_APPROVAL

            # 5. Sanitize Chain of Thought from description and metadata
            clean_description = self._sanitize_cot(step.description)
            clean_metadata = self._sanitize_metadata(step.metadata)

            sanitized_step = step.model_copy(
                update={
                    "target": target,
                    "description": clean_description,
                    "permission_level": permission_level,
                    "metadata": clean_metadata,
                }
            )
            sanitized_steps.append(sanitized_step)

        if errors:
            logger.warning("Plan validation failed with %d errors: %s", len(errors), errors)
            return PlanValidationResult(is_valid=False, errors=errors, warnings=warnings)

        clean_plan_metadata = self._sanitize_metadata(plan.metadata)
        sanitized_plan = plan.model_copy(
            update={
                "steps": sanitized_steps,
                "metadata": clean_plan_metadata,
            }
        )

        return PlanValidationResult(
            is_valid=True,
            warnings=warnings,
            sanitized_plan=sanitized_plan,
        )

    def _is_consequential_action(self, action: Action) -> bool:
        """Check if an action intends to delete, drop, or destroy resources."""
        # Check operation in parameters
        operation = str(action.parameters.get("operation", "")).lower()
        task_str = str(action.parameters.get("task", "")).lower()
        query_str = str(action.parameters.get("query", "")).lower()
        desc_str = str(action.description or "").lower()

        combined = f"{operation} {task_str} {query_str} {desc_str}"
        for keyword in CONSEQUENTIAL_KEYWORDS:
            if re.search(rf"\b{keyword}\b", combined):
                return True
        return False

    @staticmethod
    def _sanitize_cot(text: Optional[str]) -> Optional[str]:
        """Strip any thinking tags or hidden chain of thought tokens."""
        if not text:
            return text
        cleaned = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"^(Chain of thought|Internal reasoning):\s*.*?\n\n", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    @classmethod
    def _sanitize_metadata(cls, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any hidden thinking keys or thoughts from metadata."""
        if not isinstance(meta, dict):
            return {}
        cleaned: Dict[str, Any] = {}
        for k, v in meta.items():
            if k.lower() in {"thought", "thinking", "cot", "chain_of_thought", "internal_scratchpad"}:
                continue
            if isinstance(v, str):
                cleaned[k] = cls._sanitize_cot(v)
            else:
                cleaned[k] = v
        return cleaned


__all__ = [
    "PlanValidator",
    "PlanValidationResult",
    "PlanValidationError",
    "STANDARD_SYSTEM_TARGETS",
]
