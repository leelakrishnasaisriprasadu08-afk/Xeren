"""
Xeren MoS — ToolCaller (Work Assigner & Output Verifier)
=========================================================
Operating on non-autoregressive evaluator & discriminator principles (JEPA/Classifier Matrix):
1. ZERO Conversational Filler: Does not speak or generate natural language chat.
2. Phase 1 - Work Assigner:
   - Maps intent to exact specialists, tools, and actions.
   - Bundles explicit expectations (schema, syntax, max latency) and assignment confidence.
3. Phase 2 - Output Verifier:
   - High-speed validation of deliverables against expectations.
   - Computes boolean flags (passed, expectations_met, has_error, syntax_valid, needs_retry)
     and high-precision confidence floats.
   - Triggers smart micro-retries if output fails verification.
"""
from __future__ import annotations

import ast
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from .protocol import (
    AggregatedResponse,
    AssignmentExpectation,
    DispatchRequest,
    SpecialistResult,
    SpecialistTask,
    TaskAssignment,
    TaskStatus,
    VerificationVerdict,
    WorkAssignmentPlan,
)
from .specialist_registry import SpecialistID, SpecialistRegistry, SpecialistSpec
from .specialist_runner import SpecialistRunner

logger = logging.getLogger("xeren.mos.tool_caller")


class ToolCaller:
    """
    Work Assigner & Output Verifier for the Xeren Mixture of Specialists.
    """

    def __init__(
        self,
        max_parallel_specialists: int = 3,
        specialist_timeout: float = 60.0,
        runner: Optional[SpecialistRunner] = None,
        max_retries_on_verification_failure: int = 1,
    ):
        self._max_parallel = max_parallel_specialists
        self._timeout = specialist_timeout
        self._runner = runner or SpecialistRunner()
        self._max_retries = max_retries_on_verification_failure
        logger.info("[ToolCaller] initialized as Work Assigner & Output Verifier")

    # ------------------------------------------------------------------
    # Phase 1: Work Assigner
    # ------------------------------------------------------------------

    def assign(self, request: DispatchRequest) -> WorkAssignmentPlan:
        """
        Fast non-conversational work assignment matrix.
        Evaluates capabilities and produces structured TaskAssignments.
        """
        selected_specs = self._select_specialists(request)
        if not selected_specs:
            return WorkAssignmentPlan(
                trace_id=request.trace_id,
                is_executable=False,
                confidence=0.0,
                execution_strategy="sequential",
                assignments=[],
                reason_code="NO_CAPABILITY_MATCH",
            )

        selected_specs = selected_specs[: request.max_specialists]
        strategy = "parallel" if (request.allow_parallel and len(selected_specs) > 1) else "sequential"

        assignments: List[TaskAssignment] = []
        for spec in selected_specs:
            action = self._infer_action_name(spec, request.task_description)
            output_format = self._infer_output_format(spec)
            expectation = AssignmentExpectation(
                format=output_format,
                required_keys=["result"] if output_format == "json" else [],
                non_empty=True,
                syntax_check=True if output_format in ("code", "json") else False,
                max_latency_ms=self._timeout * 1000,
            )
            # High-precision confidence based on priority and capability match
            confidence = max(0.85, 1.0 - (spec.priority * 0.05))
            assignments.append(
                TaskAssignment(
                    specialist_id=spec.id.value,
                    action=action,
                    arguments={"task": request.task_description, "user_query": request.user_query},
                    expectation=expectation,
                    confidence=round(confidence, 3),
                    priority=spec.priority,
                )
            )

        avg_confidence = sum(a.confidence for a in assignments) / max(1, len(assignments))

        return WorkAssignmentPlan(
            trace_id=request.trace_id,
            is_executable=True,
            confidence=round(avg_confidence, 3),
            execution_strategy=strategy,
            assignments=assignments,
            reason_code="OPTIMAL_MATCH",
        )

    # ------------------------------------------------------------------
    # Phase 2: Output Verifier
    # ------------------------------------------------------------------

    def verify(self, task: SpecialistTask, result: SpecialistResult) -> VerificationVerdict:
        """
        Fast discriminator & verifier.
        Returns pure booleans, verification confidence, and error diagnosis.
        """
        exp = task.expectation or AssignmentExpectation()
        has_error = result.status != TaskStatus.SUCCESS or bool(result.error)
        output_text = result.output.strip() if result.output else ""
        syntax_valid = True
        expectations_met = True
        error_type: Optional[str] = None
        needs_retry = False
        retry_adjustments: Dict[str, Any] = {}
        score = 1.0

        # 1. Non-empty check
        if exp.non_empty and not output_text and not result.structured_output:
            has_error = True
            expectations_met = False
            error_type = "EMPTY_PAYLOAD"
            needs_retry = True
            score = 0.0

        # 2. Syntax validation (Code / JSON)
        if exp.syntax_check and not has_error:
            if exp.format == "code":
                # Validate python AST syntax if looks like Python
                if "def " in output_text or "import " in output_text or "class " in output_text:
                    try:
                        ast.parse(output_text)
                    except SyntaxError as syn_err:
                        syntax_valid = False
                        expectations_met = False
                        has_error = True
                        error_type = f"SYNTAX_ERROR: {syn_err.msg}"
                        needs_retry = True
                        retry_adjustments["fix_syntax_at_line"] = syn_err.lineno
                        score = 0.3
            elif exp.format == "json":
                if not result.structured_output:
                    try:
                        parsed = json.loads(output_text)
                        result.structured_output = parsed
                    except Exception as json_err:
                        syntax_valid = False
                        expectations_met = False
                        has_error = True
                        error_type = f"INVALID_JSON: {json_err}"
                        needs_retry = True
                        score = 0.2

        # 3. Required keys check
        if exp.required_keys and result.structured_output and not has_error:
            missing = [k for k in exp.required_keys if k not in result.structured_output]
            if missing:
                expectations_met = False
                has_error = True
                error_type = f"MISSING_KEYS: {missing}"
                needs_retry = True
                retry_adjustments["missing_keys"] = missing
                score = 0.5

        # 4. Latency check
        if result.execution_ms > exp.max_latency_ms:
            score = max(0.1, score - 0.2)

        passed = (not has_error) and syntax_valid and expectations_met
        verification_confidence = 0.99 if passed else 0.95

        return VerificationVerdict(
            task_trace_id=task.trace_id,
            specialist_id=task.specialist_id,
            passed=passed,
            expectations_met=expectations_met,
            confidence=verification_confidence,
            has_error=has_error,
            syntax_valid=syntax_valid,
            needs_retry=needs_retry,
            error_type=error_type,
            score=score,
            retry_adjustments=retry_adjustments,
        )

    # ------------------------------------------------------------------
    # Main Orchestrated Pipeline: Assign → Execute → Verify
    # ------------------------------------------------------------------

    async def dispatch(self, request: DispatchRequest) -> AggregatedResponse:
        """
        Full zero-bloat pipeline:
        1. assign() -> generates WorkAssignmentPlan
        2. execute  -> parallel or sequential
        3. verify() -> discriminates output with boolean flags & scores
        4. (optional retry if needs_retry)
        5. aggregate -> returns typed AggregatedResponse
        """
        t_start = time.monotonic()

        # Step 1: Work Assignment
        plan = self.assign(request)
        if not plan.is_executable or not plan.assignments:
            logger.warning("[ToolCaller] Assignment plan not executable for: %s", request.required_capabilities)
            return self._empty_response(request, warning="No specialists matched the required capabilities.")

        # Step 2: Build Specialist Tasks from Plan
        tasks = [self._build_task_from_assignment(request, a) for a in plan.assignments]

        # Step 3: Run Specialists
        if plan.execution_strategy == "parallel":
            results = await self._run_parallel(tasks)
        else:
            results = await self._run_sequential(tasks)

        # Step 4: Output Verification
        verdicts: List[VerificationVerdict] = []
        final_results: List[SpecialistResult] = []

        for task, res in zip(tasks, results):
            verdict = self.verify(task, res)
            res.verification = verdict

            # Optional self-healing retry on verification failure
            if not verdict.passed and verdict.needs_retry and self._max_retries > 0:
                logger.warning(
                    "[ToolCaller Verifier] Task '%s' failed verification (%s). Triggering smart retry...",
                    task.specialist_id,
                    verdict.error_type,
                )
                retry_task = self._build_retry_task(task, verdict)
                try:
                    retry_res = await self._runner.run(retry_task)
                    retry_verdict = self.verify(retry_task, retry_res)
                    retry_res.verification = retry_verdict
                    res = retry_res
                    verdict = retry_verdict
                except Exception as retry_err:
                    logger.error("[ToolCaller] Retry failed: %s", retry_err)

            verdicts.append(verdict)
            final_results.append(res)

        total_ms = (time.monotonic() - t_start) * 1000
        return self._aggregate(request, final_results, verdicts, total_ms)

    # ------------------------------------------------------------------
    # Specialist Selection & Task Helpers
    # ------------------------------------------------------------------

    def _select_specialists(self, request: DispatchRequest) -> List[SpecialistSpec]:
        capabilities = request.required_capabilities
        if capabilities:
            candidates: Dict[SpecialistID, SpecialistSpec] = {}
            for cap in capabilities:
                for spec in SpecialistRegistry.find_by_capability(cap):
                    if spec.id not in candidates or spec.priority < candidates[spec.id].priority:
                        candidates[spec.id] = spec
            return sorted(candidates.values(), key=lambda s: s.priority)

        return SpecialistRegistry.find_by_capability(request.task_description)

    def _infer_action_name(self, spec: SpecialistSpec, task_desc: str) -> str:
        action_map = {
            SpecialistID.CODING: "implement_code",
            SpecialistID.REASONING: "step_by_step_deduction",
            SpecialistID.RESEARCH: "research_topic",
            SpecialistID.PLANNING: "formulate_plan",
            SpecialistID.VERIFICATION: "verify_accuracy",
            SpecialistID.ANALYSIS: "analyze_patterns",
            SpecialistID.OPTIMIZATION: "optimize_performance",
        }
        return action_map.get(spec.id, "execute_task")

    def _infer_output_format(self, spec: SpecialistSpec) -> str:
        format_map = {
            SpecialistID.CODING: "code",
            SpecialistID.PLANNING: "plan",
            SpecialistID.ANALYSIS: "json",
            SpecialistID.VERIFICATION: "json",
        }
        return format_map.get(spec.id, "text")

    def _build_task_from_assignment(self, request: DispatchRequest, assignment: TaskAssignment) -> SpecialistTask:
        spec = SpecialistRegistry.get(SpecialistID(assignment.specialist_id))
        return SpecialistTask(
            dispatch_trace_id=request.trace_id,
            specialist_id=assignment.specialist_id,
            specialist_name=spec.name if spec else assignment.specialist_id,
            sub_task=self._focus_task(request.task_description, spec) if spec else request.task_description,
            input_data={
                "user_query": request.user_query,
                "context": request.context,
                "arguments": assignment.arguments,
            },
            expected_output_format=assignment.expectation.format,
            expectation=assignment.expectation,
            max_tokens=2048,
            timeout_seconds=self._timeout,
        )

    def _build_retry_task(self, original_task: SpecialistTask, verdict: VerificationVerdict) -> SpecialistTask:
        adjusted_input = dict(original_task.input_data)
        adjusted_input["verification_feedback"] = verdict.error_type
        adjusted_input["retry_adjustments"] = verdict.retry_adjustments
        return SpecialistTask(
            dispatch_trace_id=original_task.dispatch_trace_id,
            specialist_id=original_task.specialist_id,
            specialist_name=original_task.specialist_name,
            sub_task=f"{original_task.sub_task}\n\n[VERIFICATION FEEDBACK - FIX REQUIRED]: {verdict.error_type}",
            input_data=adjusted_input,
            expected_output_format=original_task.expected_output_format,
            expectation=original_task.expectation,
            max_tokens=original_task.max_tokens,
            timeout_seconds=original_task.timeout_seconds,
        )

    def _focus_task(self, task_description: str, spec: SpecialistSpec) -> str:
        focus_map = {
            SpecialistID.UNDERSTANDING: f"Identify exact intent and required context:\n{task_description}",
            SpecialistID.REASONING: f"Apply step-by-step logical reasoning to solve:\n{task_description}",
            SpecialistID.KNOWLEDGE: f"Apply domain knowledge to answer:\n{task_description}",
            SpecialistID.RESEARCH: f"Research and synthesize information for:\n{task_description}",
            SpecialistID.ANALYSIS: f"Analyze patterns and components of:\n{task_description}",
            SpecialistID.PLANNING: f"Create a step-by-step strategy for:\n{task_description}",
            SpecialistID.CODING: f"Write clean, working code for:\n{task_description}",
            SpecialistID.SIMULATION: f"Simulate possible outcomes for:\n{task_description}",
            SpecialistID.CRITIC: f"Find failure modes in:\n{task_description}",
            SpecialistID.VERIFICATION: f"Verify validity of:\n{task_description}",
            SpecialistID.OPTIMIZATION: f"Optimize the solution for:\n{task_description}",
            SpecialistID.EXPERIENCE: f"Apply learned experiences to:\n{task_description}",
            SpecialistID.TOOL_CALLER: task_description,
        }
        return focus_map.get(spec.id, task_description)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _run_parallel(self, tasks: List[SpecialistTask]) -> List[SpecialistResult]:
        coros = [self._runner.run(task) for task in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)
        return [
            r if isinstance(r, SpecialistResult) else self._error_result(task, str(r))
            for task, r in zip(tasks, results)
        ]

    async def _run_sequential(self, tasks: List[SpecialistTask]) -> List[SpecialistResult]:
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
        verdicts: List[VerificationVerdict],
        total_ms: float,
    ) -> AggregatedResponse:
        successful = [r for r in results if r.status == TaskStatus.SUCCESS]
        all_passed = all(v.passed for v in verdicts) if verdicts else False
        overall_conf = (
            sum(v.confidence for v in verdicts) / max(1, len(verdicts))
            if verdicts
            else 0.0
        )

        warnings = [
            f"{r.specialist_id}: {r.error or (r.verification.error_type if r.verification else 'Unknown error')}"
            for r in results
            if r.status == TaskStatus.FAILED or (r.verification and not r.verification.passed)
        ]

        synthesis_parts = []
        for r in successful:
            synthesis_parts.append(f"[{r.specialist_id}]:\n{r.output.strip()}")
        synthesis = "\n\n---\n\n".join(synthesis_parts) if synthesis_parts else "No specialist output available."

        best = max(successful, key=lambda r: r.confidence, default=None)
        recommended = best.output if best else synthesis

        return AggregatedResponse(
            dispatch_trace_id=request.trace_id,
            status=TaskStatus.SUCCESS if (successful and all_passed) else TaskStatus.FAILED,
            all_passed=all_passed,
            overall_confidence=round(overall_conf, 3),
            specialist_results=results,
            verification_verdicts=verdicts,
            synthesis=synthesis,
            recommended_response=recommended,
            total_specialists_used=len(successful),
            total_execution_ms=total_ms,
            warnings=warnings,
        )

    def _empty_response(self, request: DispatchRequest, warning: str = "") -> AggregatedResponse:
        return AggregatedResponse(
            dispatch_trace_id=request.trace_id,
            status=TaskStatus.SKIPPED,
            all_passed=False,
            overall_confidence=0.0,
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
