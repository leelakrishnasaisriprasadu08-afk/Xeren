"""
Xeren MoS — ToolCaller
========================
The ToolCaller is the lightweight routing model between the Main model
and the 12 specialists. It:

1. Receives a DispatchRequest from the Main model
2. Selects which specialist(s) to call based on required capabilities
3. Formats a focused SpecialistTask for each selected specialist
4. Runs specialists (parallel or sequential based on allow_parallel)
5. Aggregates all SpecialistResults into one AggregatedResponse
6. Returns the AggregatedResponse to the Main model

Architecture note:
  ToolCaller does NOT run a heavy LLM by default — it uses the
  SpecialistRegistry + rule-based routing first (fast, deterministic).
  When ambiguous, it uses the Main model's LLM to score candidates.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .protocol import (
    AggregatedResponse,
    DispatchRequest,
    SpecialistResult,
    SpecialistTask,
    TaskStatus,
)
from .specialist_registry import SpecialistID, SpecialistRegistry, SpecialistSpec
from .specialist_runner import SpecialistRunner

logger = logging.getLogger("xeren.mos.tool_caller")


class ToolCaller:
    """
    Routes tasks from the Main model to the correct specialist(s).

    Usage:
        tool_caller = ToolCaller()
        response = await tool_caller.dispatch(request)
    """

    def __init__(
        self,
        max_parallel_specialists: int = 3,
        specialist_timeout: float = 60.0,
        runner: Optional[SpecialistRunner] = None,
    ):
        self._max_parallel = max_parallel_specialists
        self._timeout = specialist_timeout
        self._runner = runner or SpecialistRunner()
        logger.info("[ToolCaller] initialized (max_parallel=%d)", max_parallel_specialists)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def dispatch(self, request: DispatchRequest) -> AggregatedResponse:
        """
        Main entry point.
        Receives a DispatchRequest, routes to specialist(s), returns aggregated result.
        """
        t_start = time.monotonic()
        logger.info(
            "[ToolCaller] dispatch trace=%s capabilities=%s",
            request.trace_id,
            request.required_capabilities,
        )

        # 1. Select specialists
        selected = self._select_specialists(request)
        if not selected:
            logger.warning("[ToolCaller] No specialists matched for capabilities: %s", request.required_capabilities)
            return self._empty_response(request, warning="No specialists matched the required capabilities.")

        # Cap to max
        selected = selected[: request.max_specialists]
        logger.info(
            "[ToolCaller] Selected %d specialist(s): %s",
            len(selected),
            [s.name for s in selected],
        )

        # 2. Build specialist tasks
        tasks = [self._build_task(request, spec) for spec in selected]

        # 3. Run specialists
        if request.allow_parallel and len(tasks) > 1:
            results = await self._run_parallel(tasks)
        else:
            results = await self._run_sequential(tasks)

        # 4. Aggregate
        total_ms = (time.monotonic() - t_start) * 1000
        return self._aggregate(request, results, total_ms)

    # ------------------------------------------------------------------
    # Specialist selection
    # ------------------------------------------------------------------

    def _select_specialists(self, request: DispatchRequest) -> List[SpecialistSpec]:
        """
        Rule-based specialist selection.
        If capabilities are listed explicitly, match against registry.
        Falls back to full-text matching on task_description.
        """
        capabilities = request.required_capabilities

        if capabilities:
            # Explicit capability routing — fastest path
            candidates: Dict[SpecialistID, SpecialistSpec] = {}
            for cap in capabilities:
                for spec in SpecialistRegistry.find_by_capability(cap):
                    # Deduplicate, keep highest priority entry
                    if spec.id not in candidates or spec.priority < candidates[spec.id].priority:
                        candidates[spec.id] = spec
            return sorted(candidates.values(), key=lambda s: s.priority)

        # Fallback: scan task description
        return SpecialistRegistry.find_by_capability(request.task_description)

    # ------------------------------------------------------------------
    # Task builder
    # ------------------------------------------------------------------

    def _build_task(self, request: DispatchRequest, spec: SpecialistSpec) -> SpecialistTask:
        return SpecialistTask(
            dispatch_trace_id=request.trace_id,
            specialist_id=spec.id.value,
            specialist_name=spec.name,
            sub_task=self._focus_task(request.task_description, spec),
            input_data={
                "user_query": request.user_query,
                "context": request.context,
            },
            expected_output_format=self._infer_output_format(spec),
            max_tokens=2048,
            timeout_seconds=self._timeout,
        )

    def _focus_task(self, task_description: str, spec: SpecialistSpec) -> str:
        """Create a specialist-specific sub-task prompt from the main task."""
        focus_map = {
            SpecialistID.UNDERSTANDING:  f"Carefully parse the following task and identify the exact intent, entities, and required context:\n{task_description}",
            SpecialistID.REASONING:      f"Apply step-by-step logical reasoning to solve:\n{task_description}",
            SpecialistID.KNOWLEDGE:      f"Apply your domain knowledge to answer:\n{task_description}",
            SpecialistID.RESEARCH:       f"Research and synthesize relevant information for:\n{task_description}",
            SpecialistID.ANALYSIS:       f"Analyze and break down the patterns and components of:\n{task_description}",
            SpecialistID.PLANNING:       f"Create a detailed step-by-step plan or strategy for:\n{task_description}",
            SpecialistID.CODING:         f"Write clean, working code to implement:\n{task_description}",
            SpecialistID.SIMULATION:     f"Simulate possible outcomes and scenarios for:\n{task_description}",
            SpecialistID.CRITIC:         f"Find weaknesses, risks, and failure modes in:\n{task_description}",
            SpecialistID.VERIFICATION:   f"Verify the correctness and validity of:\n{task_description}",
            SpecialistID.OPTIMIZATION:   f"Optimize and improve the solution for:\n{task_description}",
            SpecialistID.EXPERIENCE:     f"Apply past patterns and learned experiences to:\n{task_description}",
            SpecialistID.TOOL_CALLER:    task_description,
        }
        return focus_map.get(spec.id, task_description)

    def _infer_output_format(self, spec: SpecialistSpec) -> str:
        format_map = {
            SpecialistID.CODING:        "code",
            SpecialistID.PLANNING:      "plan",
            SpecialistID.ANALYSIS:      "json",
            SpecialistID.VERIFICATION:  "json",
        }
        return format_map.get(spec.id, "text")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _run_parallel(self, tasks: List[SpecialistTask]) -> List[SpecialistResult]:
        """Run all specialist tasks concurrently."""
        coros = [self._runner.run(task) for task in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)
        return [
            r if isinstance(r, SpecialistResult) else self._error_result(task, str(r))
            for task, r in zip(tasks, results)
        ]

    async def _run_sequential(self, tasks: List[SpecialistTask]) -> List[SpecialistResult]:
        """Run specialist tasks one after another."""
        results = []
        for task in tasks:
            try:
                result = await self._runner.run(task)
            except Exception as e:
                result = self._error_result(task, str(e))
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate(
        self,
        request: DispatchRequest,
        results: List[SpecialistResult],
        total_ms: float,
    ) -> AggregatedResponse:
        """Combine all specialist outputs into one coherent response."""
        successful = [r for r in results if r.status == TaskStatus.SUCCESS]
        warnings = [
            f"{r.specialist_id}: {r.error}"
            for r in results
            if r.status == TaskStatus.FAILED and r.error
        ]

        # Build synthesis: combine all outputs with specialist attribution
        synthesis_parts = []
        for r in successful:
            synthesis_parts.append(
                f"[{r.specialist_id}]:\n{r.output.strip()}"
            )
        synthesis = "\n\n---\n\n".join(synthesis_parts) if synthesis_parts else "No specialist output available."

        # Recommended response: use highest-confidence specialist's output as primary
        best = max(successful, key=lambda r: r.confidence, default=None)
        recommended = best.output if best else synthesis

        return AggregatedResponse(
            dispatch_trace_id=request.trace_id,
            status=TaskStatus.SUCCESS if successful else TaskStatus.FAILED,
            specialist_results=results,
            synthesis=synthesis,
            recommended_response=recommended,
            total_specialists_used=len(successful),
            total_execution_ms=total_ms,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_response(self, request: DispatchRequest, warning: str = "") -> AggregatedResponse:
        return AggregatedResponse(
            dispatch_trace_id=request.trace_id,
            status=TaskStatus.SKIPPED,
            synthesis="",
            recommended_response="",
            warnings=[warning] if warning else [],
        )

    def _error_result(self, task: SpecialistTask, error: str) -> SpecialistResult:
        return SpecialistResult(
            task_trace_id=task.trace_id,
            specialist_id=task.specialist_id,
            status=TaskStatus.FAILED,
            output="",
            error=error,
            confidence=0.0,
        )
