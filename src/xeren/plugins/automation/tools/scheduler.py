"""Scheduler interface and deterministic local scheduler for task step readiness and dynamic input resolution."""

from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional

from xeren.plugins.automation.schemas import StepStatus, TaskPlan, TaskStep


class BaseScheduler(ABC):
    """Abstract interface for task step scheduling."""

    @abstractmethod
    def get_next_runnable_steps(
        self,
        plan: TaskPlan,
        completed_step_ids: Optional[set[str]] = None,
    ) -> List[TaskStep]:
        """Determine which steps are ready for execution."""
        pass

    @abstractmethod
    def resolve_inputs(
        self,
        step: TaskStep,
        step_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Interpolate dynamic variables from dependency step outputs into step inputs."""
        pass


class DeterministicScheduler(BaseScheduler):
    """Deterministic local scheduler checking dependency completion and resolving expression bindings."""

    EXPR_PATTERN = re.compile(r"\$\{steps\.([a-zA-Z0-9_\-]+)\.output(?:\.([a-zA-Z0-9_\.]+))?\}")

    def get_next_runnable_steps(
        self,
        plan: TaskPlan,
        completed_step_ids: Optional[set[str]] = None,
    ) -> List[TaskStep]:
        """
        Return steps that are PENDING or READY and whose dependencies have all completed.
        """
        if completed_step_ids is None:
            completed_step_ids = {s.id for s in plan.steps if s.status == StepStatus.COMPLETED}

        runnable: List[TaskStep] = []
        for step in plan.steps:
            if step.status not in (StepStatus.PENDING, StepStatus.READY):
                continue
            # Check if all dependencies are completed
            if all(dep_id in completed_step_ids for dep_id in step.depends_on):
                runnable.append(step)

        return runnable

    def get_ready_steps(
        self,
        plan: TaskPlan,
        completed_step_ids: Optional[set[str]] = None,
    ) -> List[TaskStep]:
        """Alias for get_next_runnable_steps."""
        return self.get_next_runnable_steps(plan, completed_step_ids)

    def resolve_inputs(
        self,
        step: TaskStep,
        step_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Recursively resolve references in step.input_data like:
        - "${steps.step_1.output}"
        - "${steps.step_1.output.summary}"
        """
        return self._resolve_val(step.input_data, step_outputs)

    def resolve_step_inputs(self, payload: Any, step_outputs: Dict[str, Any]) -> Any:
        """Convenience method resolving inputs for either a TaskStep or an arbitrary dict/list/value."""
        if isinstance(payload, TaskStep):
            return self.resolve_inputs(payload, step_outputs)
        return self._resolve_val(payload, step_outputs)

    def _resolve_val(self, val: Any, step_outputs: Dict[str, Any]) -> Any:
        if isinstance(val, str):
            # Check if the entire string is an exact single match: "${steps.x.output}"
            exact_match = self.EXPR_PATTERN.fullmatch(val.strip())
            if exact_match:
                source_step_id = exact_match.group(1)
                attr_path = exact_match.group(2)
                output_val = step_outputs.get(source_step_id)
                if output_val is None:
                    return val
                extracted = self._extract_nested_attr(output_val, attr_path)
                return extracted if extracted is not None else val

            # Substring interpolation
            def replacer(match: re.Match[str]) -> str:
                source_id = match.group(1)
                sub_path = match.group(2)
                out = step_outputs.get(source_id)
                if out is None:
                    return ""
                resolved = self._extract_nested_attr(out, sub_path)
                return str(resolved) if resolved is not None else ""

            return self.EXPR_PATTERN.sub(replacer, val)

        elif isinstance(val, dict):
            return {k: self._resolve_val(v, step_outputs) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._resolve_val(item, step_outputs) for item in val]
        return val

    def _extract_nested_attr(self, obj: Any, path: Optional[str]) -> Any:
        if not path:
            return obj
        curr = obj
        for part in path.split("."):
            if isinstance(curr, dict):
                curr = curr.get(part)
            elif hasattr(curr, part):
                curr = getattr(curr, part)
            else:
                return None
        return curr


__all__ = ["BaseScheduler", "DeterministicScheduler"]
