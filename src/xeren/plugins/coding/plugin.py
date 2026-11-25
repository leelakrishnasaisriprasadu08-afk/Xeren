"""Coding Plugin implementation conforming to the Xeren BasePlugin contract."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.models.base import BaseLLM
from xeren.plugins.coding.manifest import CODING_PLUGIN_MANIFEST
from xeren.plugins.coding.registry import CodingToolRegistry
from xeren.plugins.coding.schemas import (
    CodingInput,
    CodingOperation,
    CodingResult,
    ExecutionConfig,
    FileArtifact,
)
from xeren.plugins.coding.tools.execution import BaseCodeExecutor
from xeren.plugins.coding.workflow import CodingWorkflow
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError

logger = logging.getLogger("xeren.plugins.coding.plugin")


class CodingPlugin(BasePlugin):
    """Modular Coding and Secure Execution Plugin for Xeren Core."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        executor: Optional[BaseCodeExecutor] = None,
        registry: Optional[CodingToolRegistry] = None,
        workflow: Optional[CodingWorkflow] = None,
    ) -> None:
        self.registry = registry or CodingToolRegistry(llm=llm, executor=executor)
        self.workflow = workflow or CodingWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return CODING_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return CodingInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return CodingResult

    def set_llm(self, llm: BaseLLM) -> None:
        """Update active LLM provider across coding tools."""
        self.registry.set_llm(llm)

    def set_executor(self, executor: BaseCodeExecutor) -> None:
        """Update active code execution sandbox backend."""
        self.registry.set_executor(executor)

    # -------------------------------------------------------------------------
    # Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute a coding operation within the sandbox boundary."""
        start_time = time.perf_counter()
        try:
            validated_input: CodingInput = self.validate_input(input_data)  # type: ignore
            # If execution context has an LLM, dynamically update registry LLM
            if context and context.llm:
                self.registry.set_llm(context.llm)

            result: CodingResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "language": result.language,
                    "diagnostics_count": len(result.diagnostics),
                    "files_count": len(result.files),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("CodingPlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"CodingPlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute a coding operation."""
        start_time = time.perf_counter()
        try:
            validated_input: CodingInput = self.validate_input(input_data)  # type: ignore
            if context and context.llm:
                self.registry.set_llm(context.llm)

            result: CodingResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "language": result.language,
                    "diagnostics_count": len(result.diagnostics),
                    "files_count": len(result.files),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("CodingPlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"CodingPlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def generate(
        self,
        task: str,
        language: str = "python",
        context_files: Optional[List[FileArtifact]] = None,
        test_code: Optional[str] = None,
        **kwargs: Any,
    ) -> CodingResult:
        """Convenience method for code generation."""
        inp = CodingInput(
            task=task,
            operation=CodingOperation.GENERATE,
            language=language,
            source_files=context_files or [],
            test_code=test_code,
            metadata=kwargs,
        )
        return self.workflow.execute_generate(inp)

    def analyze(self, source_code: str, language: str = "python", **kwargs: Any) -> CodingResult:
        """Convenience method for code analysis."""
        inp = CodingInput(
            operation=CodingOperation.ANALYZE,
            language=language,
            source_code=source_code,
            metadata=kwargs,
        )
        return self.workflow.execute_analyze(inp)

    def syntax_check(self, source_code: str, language: str = "python", **kwargs: Any) -> CodingResult:
        """Convenience method for syntax validation."""
        inp = CodingInput(
            operation=CodingOperation.SYNTAX_CHECK,
            language=language,
            source_code=source_code,
            metadata=kwargs,
        )
        return self.workflow.execute_syntax_check(inp)

    def execute_code(
        self,
        source_code: str,
        language: str = "python",
        entrypoint: str = "main.py",
        execution_config: Optional[ExecutionConfig] = None,
        **kwargs: Any,
    ) -> CodingResult:
        """Convenience method for controlled execution."""
        inp = CodingInput(
            operation=CodingOperation.EXECUTE,
            language=language,
            source_code=source_code,
            entrypoint=entrypoint,
            execution_config=execution_config or ExecutionConfig(),
            metadata=kwargs,
        )
        return self.workflow.execute_code(inp)

    def test_code(
        self,
        source_code: Optional[str] = None,
        test_code: Optional[str] = None,
        test_command: Optional[str] = None,
        language: str = "python",
        **kwargs: Any,
    ) -> CodingResult:
        """Convenience method for running tests."""
        inp = CodingInput(
            operation=CodingOperation.TEST,
            language=language,
            source_code=source_code,
            test_code=test_code,
            test_command=test_command,
            metadata=kwargs,
        )
        return self.workflow.execute_test(inp)

    def verify(
        self,
        source_code: Optional[str] = None,
        test_code: Optional[str] = None,
        language: str = "python",
        **kwargs: Any,
    ) -> CodingResult:
        """Convenience method for multi-stage verification."""
        inp = CodingInput(
            operation=CodingOperation.VERIFY,
            language=language,
            source_code=source_code,
            test_code=test_code,
            metadata=kwargs,
        )
        return self.workflow.execute_verify(inp)

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Check operational readiness of LLM and execution sandbox."""
        start_time = time.perf_counter()

        llm_ok = True
        try:
            llm_ok = self.registry.llm.ping()
        except Exception:
            llm_ok = False

        details = {
            "llm_provider": type(self.registry.llm).__name__,
            "llm_healthy": llm_ok,
            "executor_backend": type(self.registry.executor).__name__,
            "sandbox_active": True,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status = PluginHealthStatus.HEALTHY if llm_ok else PluginHealthStatus.DEGRADED

        return HealthCheckResult(
            status=status,
            details=details,
            latency_ms=latency_ms,
            error=None if llm_ok else "LLM provider health check ping failed.",
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational readiness."""
        return await asyncio.to_thread(self.health_check)

    def health(self) -> HealthCheckResult:
        """Alias for health_check conforming to plugin contract."""
        return self.health_check()

    def initialize(self) -> None:
        """Initialize plugin resources and sandbox."""
        self._initialized = True

    def shutdown(self) -> None:
        """Release plugin resources."""
        self._initialized = False


__all__ = ["CodingPlugin"]
