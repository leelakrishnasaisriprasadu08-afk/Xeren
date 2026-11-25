"""Deterministic DAG validation, cycle detection, topological sorting, and template decomposition tool."""

from collections import defaultdict, deque
import re
from typing import Dict, List, Optional, Set, Tuple

from xeren.plugins.automation.schemas import (
    RetryPolicy,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)


class TaskPlannerError(Exception):
    """Raised when task planning or DAG validation fails."""
    pass


class TaskPlannerTool:
    """
    Deterministic DAG validation, topological sorting, and template decomposition utility.

    ARCHITECTURAL BOUNDARY:
    TaskPlannerTool is strictly a deterministic execution and orchestration utility.
    It does NOT perform autonomous strategic reasoning, user intent interpretation, or
    independent decision-making about what the user wants. Those cognitive capabilities
    belong exclusively to Xeren Core + Xeren's Own LLM:

        Xeren Core + Xeren's Own LLM
                ↓ (understands intent and decides the plan/strategy)
        Automation Plugin #9
                ↓ (validates/structures the supplied plan)
        DAG / dependencies / scheduling / execution

    TaskPlannerTool performs deterministic operations:
    - DAG validation and dependency checking
    - Cycle detection (Kahn's algorithm)
    - Duplicate and self-reference detection
    - Topological ordering
    - Execution-wave generation
    - Deterministic template decomposition fallback (plan_from_objective)
    """

    def validate_dag(self, steps: List[TaskStep]) -> Tuple[bool, Optional[str]]:
        """
        Validate step IDs, dependency references, and absence of cycles in the DAG.

        Returns:
            (is_valid, error_message)
        """
        if not steps:
            return False, "Task must contain at least one step."

        step_ids: Set[str] = set()
        for step in steps:
            if not step.id or not step.id.strip():
                return False, "Step ID cannot be empty."
            if step.id in step_ids:
                return False, f"Duplicate step ID detected: '{step.id}'."
            step_ids.add(step.id)

        # Validate that all dependencies exist
        for step in steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    return False, f"Step '{step.id}' depends on non-existent step '{dep_id}'."
                if dep_id == step.id:
                    return False, f"Step '{step.id}' cannot depend on itself."

        # Detect cycles using Kahn's algorithm
        in_degree: Dict[str, int] = {s.id: 0 for s in steps}
        adj: Dict[str, List[str]] = defaultdict(list)
        for step in steps:
            for dep_id in step.depends_on:
                adj[dep_id].append(step.id)
                in_degree[step.id] += 1

        queue: deque[str] = deque([sid for sid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(steps):
            return False, "Circular dependency (cycle) detected in task execution graph."

        return True, None

    def get_topological_order(self, steps: List[TaskStep]) -> List[TaskStep]:
        """
        Return steps sorted in topological order according to depends_on constraints.
        Raises TaskPlannerError if a cycle is present.
        """
        is_valid, error = self.validate_dag(steps)
        if not is_valid:
            raise TaskPlannerError(error or "Invalid task DAG.")

        step_map: Dict[str, TaskStep] = {s.id: s for s in steps}
        in_degree: Dict[str, int] = {s.id: 0 for s in steps}
        adj: Dict[str, List[str]] = defaultdict(list)

        for step in steps:
            for dep_id in step.depends_on:
                adj[dep_id].append(step.id)
                in_degree[step.id] += 1

        queue: deque[str] = deque([sid for sid, deg in in_degree.items() if deg == 0])
        ordered: List[TaskStep] = []

        while queue:
            node = queue.popleft()
            ordered.append(step_map[node])
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return ordered

    def get_execution_waves(self, steps: List[TaskStep]) -> List[List[TaskStep]]:
        """
        Organize steps into execution waves (levels).
        Steps in wave 0 can run concurrently; wave N runs once wave N-1 dependencies complete.
        """
        is_valid, error = self.validate_dag(steps)
        if not is_valid:
            raise TaskPlannerError(error or "Invalid task DAG.")

        step_map: Dict[str, TaskStep] = {s.id: s for s in steps}
        # Compute level for each step: level = max(level of dependencies) + 1
        levels: Dict[str, int] = {}

        # Process in topological order
        ordered = self.get_topological_order(steps)
        for step in ordered:
            if not step.depends_on:
                levels[step.id] = 0
            else:
                levels[step.id] = max(levels[dep] for dep in step.depends_on) + 1

        max_level = max(levels.values()) if levels else 0
        waves: List[List[TaskStep]] = [[] for _ in range(max_level + 1)]
        for step_id, lvl in levels.items():
            waves[lvl].append(step_map[step_id])

        return waves

    def plan_from_objective(self, objective: str) -> TaskPlan:
        """
        Deterministic template-based decomposition fallback for canonical multi-step patterns.

        NOTE: Autonomous strategic reasoning and intent understanding belong to Xeren Core +
        Xeren's Own LLM. This method provides deterministic keyword/pattern mapping to standard
        plugin workflow templates when explicit steps are not provided.
        """
        text = objective.lower()
        steps: List[TaskStep] = []

        # Multi-stage canonical detection:
        # e.g. "Research competitors, analyze the data, create a website, verify it, and give me the final report"
        step_id_prefix = "step"
        step_counter = 1
        prev_id: Optional[str] = None

        has_research = any(k in text for k in ["research", "search", "investigate", "competitor"])
        has_data = any(k in text for k in ["data", "dataset", "analyze", "analytics", "clean"])
        has_coding = any(k in text for k in ["code", "coding", "script", "algorithm", "program"])
        has_website = any(k in text for k in ["website", "landing page", "web app", "html"])
        has_verification = any(k in text for k in ["verify", "verification", "validate", "check quality"])
        has_report = any(k in text for k in ["report", "summary", "synthesize", "final report"])

        if has_research:
            s_id = f"{step_id_prefix}_{step_counter}"
            step_counter += 1
            steps.append(
                TaskStep(
                    id=s_id,
                    title="Gather Research & Information",
                    plugin_name="research",
                    operation="web_search",
                    input_data={"query": objective, "depth": "quick"},
                    depends_on=[],
                )
            )
            prev_id = s_id

        if has_data:
            has_clean = any(k in text for k in ["clean", "missing", "outlier"])
            has_viz = any(k in text for k in ["visualiz", "chart", "plot"])
            has_profile = any(k in text for k in ["profile", "inspect", "summary"])

            if (has_profile or "dataset" in text) and (has_clean or has_viz):
                s1_id = f"{step_id_prefix}_{step_counter}"
                step_counter += 1
                deps = [prev_id] if prev_id else []
                steps.append(
                    TaskStep(
                        id=s1_id,
                        title="Profile Dataset",
                        plugin_name="data",
                        operation="inspect",
                        input_data={"data": "${steps." + (prev_id or "context") + ".output}"},
                        depends_on=deps,
                    )
                )
                prev_id = s1_id

                if has_clean:
                    s2_id = f"{step_id_prefix}_{step_counter}"
                    step_counter += 1
                    steps.append(
                        TaskStep(
                            id=s2_id,
                            title="Clean Dataset",
                            plugin_name="data",
                            operation="clean",
                            input_data={"data": f"${{steps.{prev_id}.output}}"},
                            depends_on=[prev_id],
                        )
                    )
                    prev_id = s2_id

                if has_viz:
                    s3_id = f"{step_id_prefix}_{step_counter}"
                    step_counter += 1
                    steps.append(
                        TaskStep(
                            id=s3_id,
                            title="Visualize Data",
                            plugin_name="data",
                            operation="visualize",
                            input_data={"data": f"${{steps.{prev_id}.output}}"},
                            depends_on=[prev_id],
                        )
                    )
                    prev_id = s3_id
            else:
                s_id = f"{step_id_prefix}_{step_counter}"
                step_counter += 1
                deps = [prev_id] if prev_id else []
                steps.append(
                    TaskStep(
                        id=s_id,
                        title="Process & Analyze Data",
                        plugin_name="data",
                        operation="inspect",
                        input_data={"data": "${steps." + (prev_id or "context") + ".output}"},
                        depends_on=deps,
                    )
                )
                prev_id = s_id

        if has_website:
            s_id = f"{step_id_prefix}_{step_counter}"
            step_counter += 1
            deps = [prev_id] if prev_id else []
            steps.append(
                TaskStep(
                    id=s_id,
                    title="Generate Website",
                    plugin_name="website",
                    operation="generate",
                    input_data={"requirement": objective},
                    depends_on=deps,
                )
            )
            prev_id = s_id
        elif has_coding:
            s_id = f"{step_id_prefix}_{step_counter}"
            step_counter += 1
            deps = [prev_id] if prev_id else []
            steps.append(
                TaskStep(
                    id=s_id,
                    title="Generate Code Solution",
                    plugin_name="coding",
                    operation="generate",
                    input_data={"prompt": objective},
                    depends_on=deps,
                )
            )
            prev_id = s_id

        if has_verification:
            s_id = f"{step_id_prefix}_{step_counter}"
            step_counter += 1
            deps = [prev_id] if prev_id else []
            steps.append(
                TaskStep(
                    id=s_id,
                    title="Verify Artifacts & Quality",
                    plugin_name="verification",
                    operation="final_response_verification",
                    input_data={"candidate": "${steps." + (prev_id or "context") + ".output}", "task": objective},
                    depends_on=deps,
                )
            )
            prev_id = s_id

        if has_report:
            s_id = f"{step_id_prefix}_{step_counter}"
            deps = [prev_id] if prev_id else []
            steps.append(
                TaskStep(
                    id=s_id,
                    title="Synthesize Final Report",
                    plugin_name="research",
                    operation="synthesize",
                    input_data={"prompt": f"Synthesize final results for: {objective}"},
                    depends_on=deps,
                )
            )
        elif not steps:
            s1_id = f"{step_id_prefix}_1"
            s2_id = f"{step_id_prefix}_2"
            steps.extend([
                TaskStep(
                    id=s1_id,
                    title="Execute Task Action",
                    plugin_name="research",
                    operation="web_search",
                    input_data={"query": objective},
                ),
                TaskStep(
                    id=s2_id,
                    title="Synthesize Results",
                    plugin_name="research",
                    operation="synthesize",
                    input_data={"prompt": f"Synthesize results for: {objective}"},
                    depends_on=[s1_id],
                ),
            ])

        return TaskPlan(
            objective=objective,
            steps=steps,
            status=TaskStatus.PLANNING,
        )

    def create_plan(
        self,
        objective: str,
        steps: Optional[List[TaskStep]] = None,
        timeout_seconds: float = 300.0,
    ) -> TaskPlan:
        """
        Create and validate a task plan from explicit steps or deterministic template fallback.
        Validates the DAG structure without autonomous strategic improvisation.
        """
        if steps:
            is_valid, error = self.validate_dag(steps)
            if not is_valid:
                raise TaskPlannerError(error or "Invalid task DAG.")
            plan_steps = steps
        else:
            plan = self.plan_from_objective(objective)
            plan_steps = plan.steps

        return TaskPlan(
            objective=objective,
            steps=plan_steps,
            timeout_seconds=timeout_seconds,
            status=TaskStatus.PENDING,
        )


__all__ = ["TaskPlannerTool", "TaskPlannerError"]
