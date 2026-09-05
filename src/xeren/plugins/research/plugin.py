"""Research Plugin implementation conforming to the Xeren BasePlugin contract."""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel

from xeren.models.base import BaseLLM
from xeren.models.providers.mock import MockLLM
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.research.manifest import RESEARCH_PLUGIN_MANIFEST
from xeren.plugins.research.schemas import ResearchInput, ResearchResult
from xeren.plugins.research.tools.registry import ResearchToolRegistry
from xeren.plugins.research.tools.live_search import create_search_engine
from xeren.plugins.research.tools.search import BaseSearchEngine, MockSearchEngine
from xeren.plugins.research.workflow import ResearchWorkflow

logger = logging.getLogger("xeren.plugins.research.plugin")


class ResearchPlugin(BasePlugin):
    """Modular Research Plugin for Xeren Core."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        search_engine: Optional[BaseSearchEngine] = None,
        tool_registry: Optional[ResearchToolRegistry] = None,
    ) -> None:
        self._llm = llm or MockLLM()
        self._search_engine = search_engine or create_search_engine()
        self.registry = tool_registry or ResearchToolRegistry(
            search_engine=self._search_engine,
            llm=self._llm,
        )
        self.workflow = ResearchWorkflow(
            tool_registry=self.registry,
            llm=self._llm,
            search_engine=self._search_engine,
        )

    @property
    def manifest(self) -> PluginManifest:
        return RESEARCH_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ResearchInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ResearchResult

    def set_llm(self, llm: BaseLLM) -> None:
        """Inject or replace the active LLM provider (e.g. when real Xeren Core LLM is ready)."""
        self._llm = llm
        self.registry.set_llm(llm)

    def set_search_engine(self, engine: BaseSearchEngine) -> None:
        """Inject or replace the active search engine provider."""
        self._search_engine = engine
        self.registry.set_search_engine(engine)
        self.workflow.registry.set_search_engine(engine)

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute the research workflow."""
        start_time = time.perf_counter()
        try:
            validated_input: ResearchInput = self.validate_input(input_data)  # type: ignore

            # If execution context supplies an explicit LLM override, update registry
            if context and context.llm:
                self.registry.set_llm(context.llm)

            # Execute the 8-step workflow
            result: ResearchResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=result,
                latency_ms=latency_ms,
                metadata={
                    "sources_analyzed": len(result.sources),
                    "evidence_count": len(result.evidence),
                    "queries_count": len(result.queries_executed),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("ResearchPlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"ResearchPlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute the research workflow."""
        start_time = time.perf_counter()
        try:
            validated_input: ResearchInput = self.validate_input(input_data)  # type: ignore

            if context and context.llm:
                self.registry.set_llm(context.llm)

            result: ResearchResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=result,
                latency_ms=latency_ms,
                metadata={
                    "sources_analyzed": len(result.sources),
                    "evidence_count": len(result.evidence),
                    "queries_count": len(result.queries_executed),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("ResearchPlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"ResearchPlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    def health_check(self) -> HealthCheckResult:
        """Check status and operational health of search engine and LLM providers."""
        start_time = time.perf_counter()
        details: Dict[str, Any] = {
            "search_engine": type(self.registry.search_engine).__name__,
            "llm": type(self._llm).__name__,
        }

        # Check search engine health
        search_ok = True
        try:
            search_ok = self.registry.search_engine.ping()
            details["search_engine_healthy"] = search_ok
        except Exception as err:
            search_ok = False
            details["search_engine_healthy"] = False
            details["search_engine_error"] = str(err)

        # Check LLM health
        llm_ok = True
        try:
            llm_ok = self._llm.ping()
            details["llm_healthy"] = llm_ok
        except Exception as err:
            llm_ok = False
            details["llm_healthy"] = False
            details["llm_error"] = str(err)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not search_ok or not llm_ok:
            status = PluginHealthStatus.DEGRADED if (search_ok or llm_ok) else PluginHealthStatus.UNHEALTHY
            return HealthCheckResult(
                status=status,
                details=details,
                latency_ms=latency_ms,
                error="One or more sub-services failed ping check.",
            )

        return HealthCheckResult(
            status=PluginHealthStatus.HEALTHY,
            details=details,
            latency_ms=latency_ms,
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational health."""
        return await asyncio.to_thread(self.health_check)


__all__ = ["ResearchPlugin"]
