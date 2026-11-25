"""Verification Plugin implementation adhering strictly to the Xeren BasePlugin contract."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.models.base import BaseLLM
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.verification.manifest import VERIFICATION_PLUGIN_MANIFEST
from xeren.plugins.verification.registry import VerificationToolRegistry
from xeren.plugins.verification.schemas import (
    CandidateItem,
    EvidenceItem,
    VerificationInput,
    VerificationOperation,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.verification.tools.judge import BaseJudge
from xeren.plugins.verification.workflow import VerificationWorkflow

logger = logging.getLogger("xeren.plugins.verification.plugin")


class VerificationPlugin(BasePlugin):
    """Production quality-control plugin evaluating outputs across modalities, facts, code, and consistency."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        judge: Optional[BaseJudge] = None,
        registry: Optional[VerificationToolRegistry] = None,
        workflow: Optional[VerificationWorkflow] = None,
    ) -> None:
        self.registry = registry or VerificationToolRegistry(llm=llm, judge=judge)
        self.workflow = workflow or VerificationWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return VERIFICATION_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return VerificationInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return VerificationResult

    def set_llm(self, llm: Optional[BaseLLM]) -> None:
        """Update or inject LLM provider for judge critiques."""
        self.registry.set_llm(llm)

    def set_judge(self, judge: BaseJudge) -> None:
        """Explicitly set a custom or test judge."""
        self.registry.set_judge(judge)

    # -------------------------------------------------------------------------
    # BasePlugin Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute a verification operation."""
        start_time = time.perf_counter()
        try:
            validated_input: VerificationInput = self.validate_input(input_data)  # type: ignore
            result: VerificationResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            is_success = result.status in (
                VerificationStatus.VERIFIED,
                VerificationStatus.PARTIALLY_VERIFIED,
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=is_success,
                output=result,
                latency_ms=latency_ms,
                error="; ".join(result.failure_reasons) if result.failure_reasons else None,
                metadata={
                    "operation": result.operation.value,
                    "status": result.status.value,
                    "confidence_score": result.confidence_score,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("VerificationPlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"VerificationPlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute a verification operation."""
        start_time = time.perf_counter()
        try:
            validated_input: VerificationInput = self.validate_input(input_data)  # type: ignore
            result: VerificationResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            is_success = result.status in (
                VerificationStatus.VERIFIED,
                VerificationStatus.PARTIALLY_VERIFIED,
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=is_success,
                output=result,
                latency_ms=latency_ms,
                error="; ".join(result.failure_reasons) if result.failure_reasons else None,
                metadata={
                    "operation": result.operation.value,
                    "status": result.status.value,
                    "confidence_score": result.confidence_score,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("VerificationPlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"VerificationPlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def verify(
        self,
        candidate: Any,
        task: Optional[str] = None,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        expected_format: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
        rubric: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.70,
        strict_mode: bool = False,
    ) -> VerificationResult:
        """Execute comprehensive final response verification across structural, evidence, consistency, and judge stages."""
        inp = VerificationInput(
            operation=VerificationOperation.FINAL_RESPONSE_VERIFICATION,
            candidate=candidate,
            task=task,
            context=context,
            evidence=evidence or [],
            expected_format=expected_format,
            schema_definition=schema_definition,
            trajectory=trajectory,
            rubric=rubric,
            confidence_threshold=confidence_threshold,
            strict_mode=strict_mode,
        )
        return self.workflow.run(inp)

    async def averify(
        self,
        candidate: Any,
        task: Optional[str] = None,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        expected_format: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
        rubric: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.70,
        strict_mode: bool = False,
    ) -> VerificationResult:
        """Asynchronously execute comprehensive final response verification."""
        inp = VerificationInput(
            operation=VerificationOperation.FINAL_RESPONSE_VERIFICATION,
            candidate=candidate,
            task=task,
            context=context,
            evidence=evidence or [],
            expected_format=expected_format,
            schema_definition=schema_definition,
            trajectory=trajectory,
            rubric=rubric,
            confidence_threshold=confidence_threshold,
            strict_mode=strict_mode,
        )
        return await self.workflow.arun(inp)

    def verify_output(
        self,
        candidate: Any,
        expected_format: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        strict_mode: bool = False,
    ) -> VerificationResult:
        """Validate output structural integrity, syntax, or schema conformance."""
        inp = VerificationInput(
            operation=VerificationOperation.OUTPUT_VALIDATION,
            candidate=candidate,
            expected_format=expected_format,
            schema_definition=schema_definition,
            strict_mode=strict_mode,
        )
        return self.workflow.run(inp)

    def fact_check(
        self,
        candidate: Any,
        evidence: Optional[List[EvidenceItem]] = None,
        strict_mode: bool = False,
    ) -> VerificationResult:
        """Ground claims against source evidence and identify unsupported assertions."""
        inp = VerificationInput(
            operation=VerificationOperation.FACT_CHECKING,
            candidate=candidate,
            evidence=evidence or [],
            strict_mode=strict_mode,
        )
        return self.workflow.run(inp)

    def rerank(
        self,
        candidates: List[CandidateItem],
        task: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        context: Optional[str] = None,
    ) -> VerificationResult:
        """Score and order candidate alternatives in descending order of quality."""
        inp = VerificationInput(
            operation=VerificationOperation.RESULT_RERANKING,
            candidates=candidates,
            task=task,
            evidence=evidence or [],
            context=context,
        )
        return self.workflow.run(inp)

    def check_consistency(
        self,
        candidate: Any,
        task: Optional[str] = None,
        context: Optional[str] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
    ) -> VerificationResult:
        """Audit candidate response for internal contradictions, task alignment, and trajectory coherence."""
        inp = VerificationInput(
            operation=VerificationOperation.CONSISTENCY_CHECKING,
            candidate=candidate,
            task=task,
            context=context,
            trajectory=trajectory,
        )
        return self.workflow.run(inp)

    def judge(
        self,
        candidate: Any,
        task: Optional[str] = None,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """Evaluate candidate response using LLM or rule-based judge."""
        inp = VerificationInput(
            operation=VerificationOperation.LLM_JUDGE,
            candidate=candidate,
            task=task,
            context=context,
            evidence=evidence or [],
            rubric=rubric,
        )
        return self.workflow.run(inp)

    def score_confidence(
        self,
        candidate: Any,
        task: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
        strict_mode: bool = False,
    ) -> VerificationResult:
        """Perform multi-signal confidence scoring across candidate and context."""
        inp = VerificationInput(
            operation=VerificationOperation.CONFIDENCE_SCORING,
            candidate=candidate,
            task=task,
            evidence=evidence or [],
            trajectory=trajectory,
            strict_mode=strict_mode,
        )
        return self.workflow.run(inp)

    def verify_code(
        self,
        code: str,
        task: Optional[str] = None,
        strict_mode: bool = False,
    ) -> VerificationResult:
        """Verify code syntax, completeness, and task alignment."""
        inp = VerificationInput(
            operation=VerificationOperation.CODE_VERIFICATION,
            candidate=code,
            task=task,
            strict_mode=strict_mode,
        )
        return self.workflow.run(inp)

    def verify_data(
        self,
        data: Any,
        schema_definition: Optional[Dict[str, Any]] = None,
        strict_mode: bool = False,
    ) -> VerificationResult:
        """Verify data schema uniformity, record completeness, and structure."""
        inp = VerificationInput(
            operation=VerificationOperation.DATA_VERIFICATION,
            candidate=data,
            schema_definition=schema_definition,
            strict_mode=strict_mode,
        )
        return self.workflow.run(inp)

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Check operational readiness of VerificationPlugin."""
        start_time = time.perf_counter()
        if not self._initialized:
            return HealthCheckResult(
                status=PluginHealthStatus.UNHEALTHY,
                details={"initialized": False, "tools_ready": False},
                latency_ms=0.0,
                error="VerificationPlugin is not initialized",
            )

        details = {
            "initialized": True,
            "judge_type": type(self.registry.judge).__name__,
            "has_llm_judge": isinstance(self.registry.judge, BaseJudge),
            "registered_tools_count": 6,
            "tools_ready": True,
            "supported_capabilities": self.manifest.capabilities,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return HealthCheckResult(
            status=PluginHealthStatus.HEALTHY,
            details=details,
            latency_ms=latency_ms,
            error=None,
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational readiness."""
        return await asyncio.to_thread(self.health_check)

    def health(self) -> HealthCheckResult:
        """Alias conforming to standard plugin contract."""
        return self.health_check()

    def initialize(self) -> None:
        """Initialize plugin state."""
        self._initialized = True

    def shutdown(self) -> None:
        """Release plugin resources."""
        self._initialized = False


__all__ = ["VerificationPlugin"]
