"""Workflow orchestrator executing multi-stage verification pipelines across all operations."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from xeren.plugins.verification.registry import VerificationToolRegistry
from xeren.plugins.verification.schemas import (
    CandidateItem,
    CheckResult,
    EvidenceItem,
    JudgeVerdict,
    VerificationInput,
    VerificationOperation,
    VerificationResult,
    VerificationStatus,
)

logger = logging.getLogger("xeren.plugins.verification.workflow")


class VerificationWorkflow:
    """Orchestrates multi-stage deterministic, grounding, consistency, judge, and scoring verification."""

    def __init__(self, registry: Optional[VerificationToolRegistry] = None) -> None:
        self.registry = registry or VerificationToolRegistry()

    def run(self, input_data: VerificationInput) -> VerificationResult:
        """Synchronously execute the verification pipeline for the requested operation."""
        start = time.perf_counter()

        op = input_data.operation
        if input_data.expected_conditions:
            corpus = str(input_data.candidate or "")
            for cond in input_data.expected_conditions:
                if cond.startswith("contains "):
                    req = cond.replace("contains ", "").strip()
                    if req not in corpus:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            operation=op,
                            confidence_score=0.0,
                            failure_reasons=[f"Condition not satisfied: {cond}"],
                            latency_ms=(time.perf_counter() - start) * 1000.0,
                        )
        if not input_data.success:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                operation=op,
                confidence_score=0.0,
                failure_reasons=["Task reported failure"],
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )

        if op == VerificationOperation.OUTPUT_VALIDATION:
            res = self._execute_output_validation(input_data)
        elif op == VerificationOperation.FACT_CHECKING:
            res = self._execute_fact_checking(input_data)
        elif op == VerificationOperation.RESULT_RERANKING:
            res = self._execute_reranking(input_data)
        elif op == VerificationOperation.CONSISTENCY_CHECKING:
            res = self._execute_consistency_checking(input_data)
        elif op == VerificationOperation.CODE_VERIFICATION:
            res = self._execute_code_verification(input_data)
        elif op == VerificationOperation.DATA_VERIFICATION:
            res = self._execute_data_verification(input_data)
        elif op == VerificationOperation.SOURCE_EVIDENCE_CHECK:
            res = self._execute_source_evidence_check(input_data)
        elif op == VerificationOperation.CONFIDENCE_SCORING:
            res = self._execute_confidence_scoring(input_data)
        elif op == VerificationOperation.LLM_JUDGE:
            res = self._execute_llm_judge(input_data, is_async=False)
        elif op == VerificationOperation.FINAL_RESPONSE_VERIFICATION:
            res = self._execute_final_response_verification(input_data, is_async=False)
        else:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return VerificationResult(
                status=VerificationStatus.FAILED,
                operation=op,
                confidence_score=0.0,
                failure_reasons=[f"Unsupported verification operation: '{op}'"],
                latency_ms=round(elapsed_ms, 2),
            )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return res.model_copy(update={"latency_ms": round(elapsed_ms, 2)})

    async def arun(self, input_data: VerificationInput) -> VerificationResult:
        """Asynchronously execute verification with native async judge support."""
        start = time.perf_counter()
        op = input_data.operation

        if input_data.expected_conditions:
            corpus = str(input_data.candidate or "")
            for cond in input_data.expected_conditions:
                if cond.startswith("contains "):
                    req = cond.replace("contains ", "").strip()
                    if req not in corpus:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            operation=op,
                            confidence_score=0.0,
                            failure_reasons=[f"Condition not satisfied: {cond}"],
                            latency_ms=(time.perf_counter() - start) * 1000.0,
                        )
        if not input_data.success:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                operation=op,
                confidence_score=0.0,
                failure_reasons=["Task reported failure"],
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )

        if op == VerificationOperation.LLM_JUDGE:
            res = await self._aexecute_llm_judge(input_data)
        elif op == VerificationOperation.FINAL_RESPONSE_VERIFICATION:
            res = await self._aexecute_final_response_verification(input_data)
        else:
            # CPU-bound / deterministic operations can run in threadpool
            res = await asyncio.to_thread(self.run, input_data)
            return res

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return res.model_copy(update={"latency_ms": round(elapsed_ms, 2)})

    # -------------------------------------------------------------------------
    # Individual Operation Handlers
    # -------------------------------------------------------------------------

    def _execute_output_validation(self, input_data: VerificationInput) -> VerificationResult:
        checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format=input_data.expected_format,
            schema_definition=input_data.schema_definition,
            operation=input_data.operation,
        )
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=checks,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=checks,
            failure_reasons=fails,
            actionable_corrections=fixes,
        )

    def _execute_fact_checking(self, input_data: VerificationInput) -> VerificationResult:
        ev_checks, grounding, provenance, unsupported, is_unverifiable = (
            self.registry.evidence_tool.verify_evidence(
                candidate=input_data.candidate,
                evidence=input_data.evidence,
                operation=input_data.operation,
            )
        )
        # Structural check
        struct_checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format=input_data.expected_format,
            operation=input_data.operation,
        )
        all_checks = struct_checks + ev_checks

        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=all_checks,
            grounding_score=grounding,
            is_unverifiable=is_unverifiable,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=all_checks,
            failure_reasons=fails,
            actionable_corrections=fixes,
            evidence_grounding_score=grounding,
            provenance=provenance,
            raw_details={"unsupported_claims": unsupported},
        )

    def _execute_reranking(self, input_data: VerificationInput) -> VerificationResult:
        candidates = input_data.candidates
        if not candidates and input_data.candidate is not None:
            candidates = [
                CandidateItem(
                    id="primary_candidate",
                    content=input_data.candidate,
                    metadata={"source": "primary"},
                )
            ]

        if not candidates:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                operation=input_data.operation,
                confidence_score=0.0,
                failure_reasons=["No candidates provided for reranking."],
                actionable_corrections=["Provide a list of CandidateItem to rerank."],
            )

        reranked = self.registry.reranker_tool.rerank(
            candidates=candidates,
            task=input_data.task,
            evidence=input_data.evidence,
            context=input_data.context,
        )

        top_score = reranked[0].score if reranked and reranked[0].score is not None else 0.5
        status = (
            VerificationStatus.VERIFIED
            if top_score >= input_data.confidence_threshold
            else VerificationStatus.PARTIALLY_VERIFIED
        )

        check = CheckResult(
            name="reranking_completion_check",
            passed=True,
            score=top_score,
            reason=f"Successfully scored and ordered {len(reranked)} candidates; top score {top_score:.2f}.",
        )

        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=top_score,
            checks=[check],
            reranked_candidates=reranked,
            raw_details={"top_candidate_id": reranked[0].id if reranked else None},
        )

    def _execute_consistency_checking(self, input_data: VerificationInput) -> VerificationResult:
        checks, consistency_score = self.registry.consistency_tool.check_consistency(
            candidate=input_data.candidate,
            task=input_data.task,
            context=input_data.context,
            trajectory=input_data.trajectory,
        )
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=checks,
            consistency_score=consistency_score,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=checks,
            failure_reasons=fails,
            actionable_corrections=fixes,
            consistency_score=consistency_score,
        )

    def _execute_code_verification(self, input_data: VerificationInput) -> VerificationResult:
        checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format="python",
            operation=VerificationOperation.CODE_VERIFICATION,
        )
        # Check task alignment if task provided
        if input_data.task:
            align_checks, _ = self.registry.consistency_tool.check_consistency(
                candidate=input_data.candidate,
                task=input_data.task,
            )
            for c in align_checks:
                if c.name == "task_alignment_check":
                    checks.append(c)

        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=checks,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=checks,
            failure_reasons=fails,
            actionable_corrections=fixes,
        )

    def _execute_data_verification(self, input_data: VerificationInput) -> VerificationResult:
        checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            schema_definition=input_data.schema_definition,
            operation=VerificationOperation.DATA_VERIFICATION,
        )
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=checks,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=checks,
            failure_reasons=fails,
            actionable_corrections=fixes,
        )

    def _execute_source_evidence_check(self, input_data: VerificationInput) -> VerificationResult:
        checks, grounding, provenance, unsupported, is_unverifiable = (
            self.registry.evidence_tool.verify_evidence(
                candidate=input_data.candidate,
                evidence=input_data.evidence,
                operation=input_data.operation,
            )
        )
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=checks,
            grounding_score=grounding,
            is_unverifiable=is_unverifiable,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=checks,
            failure_reasons=fails,
            actionable_corrections=fixes,
            evidence_grounding_score=grounding,
            provenance=provenance,
            raw_details={"unsupported_claims": unsupported},
        )

    def _execute_confidence_scoring(self, input_data: VerificationInput) -> VerificationResult:
        struct_checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format=input_data.expected_format,
            schema_definition=input_data.schema_definition,
        )
        ev_checks, grounding, _, _, is_unverifiable = (
            self.registry.evidence_tool.verify_evidence(
                candidate=input_data.candidate,
                evidence=input_data.evidence,
                operation=input_data.operation,
            )
        )
        cons_checks, cons_score = self.registry.consistency_tool.check_consistency(
            candidate=input_data.candidate,
            task=input_data.task,
            context=input_data.context,
            trajectory=input_data.trajectory,
        )
        all_checks = struct_checks + ev_checks + cons_checks
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=all_checks,
            grounding_score=grounding if input_data.evidence else None,
            consistency_score=cons_score,
            is_unverifiable=is_unverifiable,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=all_checks,
            failure_reasons=fails,
            actionable_corrections=fixes,
            evidence_grounding_score=grounding if input_data.evidence else None,
            consistency_score=cons_score,
        )

    def _execute_llm_judge(
        self, input_data: VerificationInput, is_async: bool = False
    ) -> VerificationResult:
        struct_checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format=input_data.expected_format,
        )
        verdict = self.registry.judge.judge(
            task=input_data.task,
            candidate=input_data.candidate,
            context=input_data.context,
            evidence=input_data.evidence,
            rubric=input_data.rubric,
        )
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=struct_checks,
            judge_verdict=verdict,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=struct_checks,
            judge_verdict=verdict,
            failure_reasons=fails,
            actionable_corrections=fixes,
        )

    async def _aexecute_llm_judge(self, input_data: VerificationInput) -> VerificationResult:
        struct_checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format=input_data.expected_format,
        )
        verdict = await self.registry.judge.ajudge(
            task=input_data.task,
            candidate=input_data.candidate,
            context=input_data.context,
            evidence=input_data.evidence,
            rubric=input_data.rubric,
        )
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=struct_checks,
            judge_verdict=verdict,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )
        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=struct_checks,
            judge_verdict=verdict,
            failure_reasons=fails,
            actionable_corrections=fixes,
        )

    def _execute_final_response_verification(
        self, input_data: VerificationInput, is_async: bool = False
    ) -> VerificationResult:
        # Full multi-stage pipeline
        # 1. Structural checks
        checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format=input_data.expected_format,
            schema_definition=input_data.schema_definition,
        )

        # 2. Source evidence grounding (if evidence provided)
        grounding_score: Optional[float] = None
        provenance: Dict[str, Any] = {}
        if input_data.evidence:
            ev_checks, grounding, prov, _, is_unverifiable = (
                self.registry.evidence_tool.verify_evidence(
                    candidate=input_data.candidate,
                    evidence=input_data.evidence,
                    operation=input_data.operation,
                )
            )
            checks.extend(ev_checks)
            grounding_score = grounding
            provenance = prov

        # 3. Consistency checks
        cons_checks, cons_score = self.registry.consistency_tool.check_consistency(
            candidate=input_data.candidate,
            task=input_data.task,
            context=input_data.context,
            trajectory=input_data.trajectory,
        )
        checks.extend(cons_checks)

        # 4. Judge evaluation
        judge_verdict = self.registry.judge.judge(
            task=input_data.task,
            candidate=input_data.candidate,
            context=input_data.context,
            evidence=input_data.evidence,
            rubric=input_data.rubric,
        )

        # 5. Composite calibrated confidence & status
        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=checks,
            judge_verdict=judge_verdict,
            grounding_score=grounding_score,
            consistency_score=cons_score,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )

        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=checks,
            judge_verdict=judge_verdict,
            failure_reasons=fails,
            actionable_corrections=fixes,
            evidence_grounding_score=grounding_score,
            consistency_score=cons_score,
            provenance=provenance,
        )

    async def _aexecute_final_response_verification(
        self, input_data: VerificationInput
    ) -> VerificationResult:
        # Full multi-stage pipeline with native async judge
        checks = self.registry.validator_tool.validate(
            candidate=input_data.candidate,
            expected_format=input_data.expected_format,
            schema_definition=input_data.schema_definition,
        )

        grounding_score: Optional[float] = None
        provenance: Dict[str, Any] = {}
        if input_data.evidence:
            ev_checks, grounding, prov, _, is_unverifiable = (
                self.registry.evidence_tool.verify_evidence(
                    candidate=input_data.candidate,
                    evidence=input_data.evidence,
                    operation=input_data.operation,
                )
            )
            checks.extend(ev_checks)
            grounding_score = grounding
            provenance = prov

        cons_checks, cons_score = self.registry.consistency_tool.check_consistency(
            candidate=input_data.candidate,
            task=input_data.task,
            context=input_data.context,
            trajectory=input_data.trajectory,
        )
        checks.extend(cons_checks)

        judge_verdict = await self.registry.judge.ajudge(
            task=input_data.task,
            candidate=input_data.candidate,
            context=input_data.context,
            evidence=input_data.evidence,
            rubric=input_data.rubric,
        )

        status, conf, fails, fixes = self.registry.confidence_tool.score(
            checks=checks,
            judge_verdict=judge_verdict,
            grounding_score=grounding_score,
            consistency_score=cons_score,
            confidence_threshold=input_data.confidence_threshold,
            strict_mode=input_data.strict_mode,
            operation=input_data.operation,
        )

        return VerificationResult(
            status=status,
            operation=input_data.operation,
            confidence_score=conf,
            checks=checks,
            judge_verdict=judge_verdict,
            failure_reasons=fails,
            actionable_corrections=fixes,
            evidence_grounding_score=grounding_score,
            consistency_score=cons_score,
            provenance=provenance,
        )


__all__ = ["VerificationWorkflow"]
