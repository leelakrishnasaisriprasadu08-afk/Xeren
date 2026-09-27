"""Experience Plugin implementation adhering strictly to the Xeren BasePlugin contract."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.experience.manifest import EXPERIENCE_PLUGIN_MANIFEST
from xeren.plugins.experience.registry import ExperienceToolRegistry
from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
    ExperienceStats,
    FailureWarning,
    LessonItem,
    UserFeedback,
)
from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.workflow import ExperienceWorkflow

logger = logging.getLogger("xeren.plugins.experience.plugin")


class ExperiencePlugin(BasePlugin):
    """Structured experience memory layer tracking outcomes, user feedback, lessons, and failure avoidance."""

    def __init__(
        self,
        store: Optional[BaseExperienceStore] = None,
        registry: Optional[ExperienceToolRegistry] = None,
        workflow: Optional[ExperienceWorkflow] = None,
    ) -> None:
        self.registry = registry or ExperienceToolRegistry(store=store)
        self.workflow = workflow or ExperienceWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return EXPERIENCE_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ExperienceInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ExperienceResult

    @property
    def store(self) -> BaseExperienceStore:
        """Active storage backend."""
        return self.registry.store

    def set_store(self, store: BaseExperienceStore) -> None:
        """Swap persistence backend."""
        self.registry.set_store(store)

    # -------------------------------------------------------------------------
    # BasePlugin Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute an experience operation."""
        start_time = time.perf_counter()
        try:
            validated_input: ExperienceInput = self.validate_input(input_data)  # type: ignore
            result: ExperienceResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "count": len(result.experiences),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("ExperiencePlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"ExperiencePlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute an experience operation."""
        start_time = time.perf_counter()
        try:
            validated_input: ExperienceInput = self.validate_input(input_data)  # type: ignore
            result: ExperienceResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "count": len(result.experiences),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("ExperiencePlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"ExperiencePlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def record(
        self,
        task: str,
        context: Optional[str] = None,
        plugin_name: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Any = None,
        success: bool = True,
        verification_status: Optional[str] = None,
        verification_score: Optional[float] = None,
        confidence: float = 1.0,
        lesson: Optional[str] = None,
        failure_reason: Optional[str] = None,
        failure_avoidance_advice: Optional[str] = None,
        error: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExperienceResult:
        """Record a completed task outcome into experience memory."""
        item = ExperienceItem(
            task=task,
            context=context,
            selected_plugin=plugin_name,
            action=action,
            outcome=outcome,
            success=success,
            verification_status=verification_status,
            verification_score=verification_score,
            confidence=confidence,
            lesson=lesson,
            failure_reason=failure_reason,
            failure_avoidance_advice=failure_avoidance_advice,
            error=error,
            tags=tags or [],
            metadata=metadata or {},
        )
        inp = ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            item=item,
        )
        return self.workflow.run(inp)

    def retrieve(
        self,
        task: Optional[str] = None,
        filter_plugin: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 5,
    ) -> ExperienceResult:
        """Retrieve and rank relevant past experiences."""
        inp = ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RETRIEVAL,
            task=task,
            filter_plugin=filter_plugin,
            success=success,
            limit=limit,
        )
        return self.workflow.run(inp)

    def add_feedback(
        self,
        experience_id: str,
        rating: Optional[int] = None,
        thumbs_up: Optional[bool] = None,
        comments: Optional[str] = None,
        corrected_outcome: Optional[str] = None,
    ) -> ExperienceResult:
        """Attach user rating or correction to an experience record."""
        feedback = UserFeedback(
            rating=rating,
            thumbs_up=thumbs_up,
            comments=comments,
            corrected_outcome=corrected_outcome,
        )
        inp = ExperienceInput(
            operation=ExperienceOperation.USER_FEEDBACK,
            experience_id=experience_id,
            user_feedback=feedback,
        )
        return self.workflow.run(inp)

    def get_success_history(
        self, limit: int = 10, plugin: Optional[str] = None
    ) -> List[ExperienceItem]:
        """Query verified successful experiences."""
        inp = ExperienceInput(
            operation=ExperienceOperation.SUCCESS_HISTORY,
            filter_plugin=plugin,
            limit=limit,
        )
        res = self.workflow.run(inp)
        return res.experiences

    def get_failure_history(
        self, limit: int = 10, plugin: Optional[str] = None
    ) -> List[ExperienceItem]:
        """Query failed experiences."""
        inp = ExperienceInput(
            operation=ExperienceOperation.FAILURE_HISTORY,
            filter_plugin=plugin,
            limit=limit,
        )
        res = self.workflow.run(inp)
        return res.experiences

    def avoid_failures(
        self, task: str, limit: int = 5, plugin: Optional[str] = None
    ) -> List[FailureWarning]:
        """Retrieve failure warnings relevant to a target task."""
        inp = ExperienceInput(
            operation=ExperienceOperation.FAILURE_AVOIDANCE,
            task=task,
            filter_plugin=plugin,
            limit=limit,
        )
        res = self.workflow.run(inp)
        return res.failure_warnings

    def extract_lessons(
        self, task: Optional[str] = None, plugin: Optional[str] = None, limit: int = 10
    ) -> List[LessonItem]:
        """Extract distilled lessons from recorded experience history."""
        inp = ExperienceInput(
            operation=ExperienceOperation.LESSON_EXTRACTION,
            task=task,
            filter_plugin=plugin,
            limit=limit,
        )
        res = self.workflow.run(inp)
        return res.lessons

    def track_outcomes(self) -> ExperienceStats:
        """Compute aggregated experience statistics."""
        inp = ExperienceInput(operation=ExperienceOperation.OUTCOME_TRACKING)
        res = self.workflow.run(inp)
        return res.stats or ExperienceStats()

    def get_decision_context(self, task: str, limit: int = 3) -> Optional[str]:
        """Retrieve past experiences and return formatted decision context for Core LLM prompts."""
        res = self.retrieve(task=task, limit=limit)
        return res.decision_context

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Check operational readiness of ExperiencePlugin."""
        start_time = time.perf_counter()
        if not self._initialized:
            return HealthCheckResult(
                status=PluginHealthStatus.UNHEALTHY,
                details={"initialized": False, "store_ready": False},
                latency_ms=0.0,
                error="ExperiencePlugin is not initialized",
            )

        store_type = type(self.store).__name__
        total_items = self.store.count()
        details = {
            "initialized": True,
            "store_type": store_type,
            "stored_experiences_count": total_items,
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


__all__ = ["ExperiencePlugin"]
