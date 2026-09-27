"""Website Creation Plugin implementation conforming to the Xeren BasePlugin contract."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.models.base import BaseLLM
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.website.manifest import WEBSITE_PLUGIN_MANIFEST
from xeren.plugins.website.registry import WebsiteToolRegistry
from xeren.plugins.website.schemas import (
    WebsiteInput,
    WebsiteOperation,
    WebsiteResult,
    WebsiteType,
)
from xeren.plugins.website.tools.preview import BasePreviewProvider
from xeren.plugins.website.workflow import WebsiteWorkflow

logger = logging.getLogger("xeren.plugins.website.plugin")


class WebsitePlugin(BasePlugin):
    """Modular Website Creation, Validation, and Security Plugin for Xeren Core."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        coding_plugin: Optional[CodingPlugin] = None,
        preview_provider: Optional[BasePreviewProvider] = None,
        registry: Optional[WebsiteToolRegistry] = None,
        workflow: Optional[WebsiteWorkflow] = None,
    ) -> None:
        self.registry = registry or WebsiteToolRegistry(
            llm=llm,
            coding_plugin=coding_plugin,
            preview_provider=preview_provider,
        )
        self.workflow = workflow or WebsiteWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return WEBSITE_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return WebsiteInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return WebsiteResult

    def set_llm(self, llm: BaseLLM) -> None:
        """Update active LLM provider across website tools."""
        self.registry.set_llm(llm)

    def set_coding_plugin(self, plugin: CodingPlugin) -> None:
        """Update active CodingPlugin dependency."""
        self.registry.set_coding_plugin(plugin)

    def set_preview_provider(self, provider: BasePreviewProvider) -> None:
        """Update active preview provider."""
        self.registry.set_preview_provider(provider)

    # -------------------------------------------------------------------------
    # BasePlugin Execution Contract
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute a website operation."""
        start_time = time.perf_counter()
        try:
            validated_input: WebsiteInput = self.validate_input(input_data)  # type: ignore
            if context and context.llm:
                self.registry.set_llm(context.llm)

            result: WebsiteResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "website_type": result.website_type,
                    "files_count": len(result.files),
                    "diagnostics_count": len(result.diagnostics),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("WebsitePlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"WebsitePlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute a website operation."""
        start_time = time.perf_counter()
        try:
            validated_input: WebsiteInput = self.validate_input(input_data)  # type: ignore
            if context and context.llm:
                self.registry.set_llm(context.llm)

            result: WebsiteResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "website_type": result.website_type,
                    "files_count": len(result.files),
                    "diagnostics_count": len(result.diagnostics),
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("WebsitePlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"WebsitePlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def generate_website(
        self,
        requirement: str,
        website_type: Union[WebsiteType, str] = WebsiteType.LANDING_PAGE,
        pages: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> WebsiteResult:
        """Convenience method for end-to-end website generation."""
        inp = WebsiteInput(
            requirement=requirement,
            operation=WebsiteOperation.GENERATE,
            website_type=website_type,
            pages=pages or [],
            features=features or [],
            metadata=kwargs,
        )
        return self.workflow.execute_generate(inp)

    def edit_website(
        self,
        existing_files: List[FileArtifact],
        modification_request: str,
        **kwargs: Any,
    ) -> WebsiteResult:
        """Convenience method for modifying an existing website."""
        inp = WebsiteInput(
            existing_files=existing_files,
            modification_request=modification_request,
            operation=WebsiteOperation.EDIT,
            metadata=kwargs,
        )
        return self.workflow.execute_edit(inp)

    def validate_website(
        self,
        files: List[FileArtifact],
        **kwargs: Any,
    ) -> WebsiteResult:
        """Convenience method for validating website files."""
        inp = WebsiteInput(
            existing_files=files,
            operation=WebsiteOperation.VALIDATE,
            metadata=kwargs,
        )
        return self.workflow.execute_validate(inp)

    def security_check(
        self,
        files: List[FileArtifact],
        **kwargs: Any,
    ) -> WebsiteResult:
        """Convenience method for static security checking."""
        inp = WebsiteInput(
            existing_files=files,
            operation=WebsiteOperation.SECURITY_CHECK,
            metadata=kwargs,
        )
        return self.workflow.execute_security_check(inp)

    def verify_website(
        self,
        files: List[FileArtifact],
        **kwargs: Any,
    ) -> WebsiteResult:
        """Convenience method for complete verification."""
        inp = WebsiteInput(
            existing_files=files,
            operation=WebsiteOperation.VERIFY,
            metadata=kwargs,
        )
        return self.workflow.execute_verify(inp)

    def analyze_requirements(
        self,
        requirement: str,
        website_type: Union[WebsiteType, str] = WebsiteType.LANDING_PAGE,
        **kwargs: Any,
    ) -> WebsiteResult:
        """Convenience method for requirement analysis."""
        inp = WebsiteInput(
            requirement=requirement,
            operation=WebsiteOperation.ANALYZE_REQUIREMENTS,
            website_type=website_type,
            metadata=kwargs,
        )
        return self.workflow.execute_analyze_requirements(inp)

    def preview_website(
        self,
        files: List[FileArtifact],
        preview_options: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> WebsiteResult:
        """Convenience method for previewing website files."""
        inp = WebsiteInput(
            existing_files=files,
            operation=WebsiteOperation.PREVIEW,
            preview_options=preview_options or {},
            metadata=kwargs,
        )
        return self.workflow.execute_preview(inp)

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Check operational readiness of LLM and underlying CodingPlugin."""
        start_time = time.perf_counter()

        llm_ok = True
        try:
            llm_ok = self.registry.llm.ping()
        except Exception:
            llm_ok = False

        coding_health = self.registry.coding_plugin.health_check()
        coding_ok = coding_health.status == PluginHealthStatus.HEALTHY

        details = {
            "llm_provider": type(self.registry.llm).__name__,
            "llm_healthy": llm_ok,
            "coding_plugin_healthy": coding_ok,
            "preview_provider": type(self.registry.preview_provider).__name__,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status = PluginHealthStatus.HEALTHY if (llm_ok and coding_ok) else PluginHealthStatus.DEGRADED

        error_msg = None
        if not llm_ok:
            error_msg = "LLM ping check failed."
        elif not coding_ok:
            error_msg = f"Underlying CodingPlugin unhealthy: {coding_health.error}"

        return HealthCheckResult(
            status=status,
            details=details,
            latency_ms=latency_ms,
            error=error_msg,
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


__all__ = ["WebsitePlugin"]
