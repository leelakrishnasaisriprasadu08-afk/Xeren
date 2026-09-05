"""Reusable plugin contract and base abstractions for Xeren modular plugins."""

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Type, Union
import uuid

from pydantic import BaseModel, Field

from xeren.models.base import BaseLLM
from xeren.plugins.errors import PluginValidationError


class PluginCapability(str, Enum):
    """Enumeration of standard capabilities exposed by Xeren plugins."""

    WEB_SEARCH = "web_search"
    QUERY_GENERATION = "query_generation"
    SOURCE_RANKING = "source_ranking"
    EVIDENCE_EXTRACTION = "evidence_extraction"
    SYNTHESIS = "synthesis"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    KNOWLEDGE_INGESTION = "knowledge_ingestion"
    CONTEXT_BUILDING = "context_building"
    RERANKING = "reranking"
    CODE_EXECUTION = "code_execution"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    SYNTAX_CHECKING = "syntax_checking"
    TEST_EXECUTION = "test_execution"
    CODE_VERIFICATION = "code_verification"
    CODE_MODIFICATION = "code_modification"
    DATA_ANALYSIS = "data_analysis"
    DATA_INGESTION = "data_ingestion"
    DATA_INSPECTION = "data_inspection"
    DATA_CLEANING = "data_cleaning"
    DATA_TRANSFORMATION = "data_transformation"
    DATA_VISUALIZATION = "data_visualization"
    DATA_VERIFICATION = "data_verification"
    WEBSITE_REQUIREMENT_ANALYSIS = "website_requirement_analysis"
    WEBSITE_GENERATION = "website_generation"
    WEBSITE_MODIFICATION = "website_modification"
    WEBSITE_VALIDATION = "website_validation"
    WEBSITE_SECURITY_CHECK = "website_security_check"
    WEBSITE_PREVIEW = "website_preview"
    CUSTOM = "custom"


class PluginHealthStatus(str, Enum):
    """Operational health status of a plugin."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult(BaseModel):
    """Payload representing health and status information for a plugin."""

    status: PluginHealthStatus = Field(..., description="Overall health status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic and component health details")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Health check latency in milliseconds")
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when check was performed",
    )
    error: Optional[str] = Field(default=None, description="Diagnostic error if unhealthy")


class PluginManifest(BaseModel):
    """Metadata specification describing a plugin and its interface."""

    name: str = Field(..., description="Unique lowercase plugin identifier")
    version: str = Field(..., description="Semantic version string (e.g. 0.1.0)")
    description: str = Field(..., description="Human-readable description of plugin functionality")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities provided by plugin")
    input_schema_name: str = Field(..., description="Name of the input Pydantic schema")
    output_schema_name: str = Field(..., description="Name of the output Pydantic schema")
    author: Optional[str] = Field(default="Xeren", description="Author or maintainer of the plugin")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")


class PluginExecutionContext(BaseModel):
    """Runtime context passed into plugin executions."""

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Traceable execution identifier")
    timeout_seconds: Optional[float] = Field(default=None, gt=0.0, description="Execution timeout limit in seconds")
    llm: Optional[BaseLLM] = Field(default=None, description="Injected core LLM provider")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual metadata from Xeren Core")

    model_config = {"arbitrary_types_allowed": True}


class PluginExecutionResult(BaseModel):
    """Standardized wrapper for plugin execution outcomes."""

    plugin_name: str = Field(..., description="Name of the executing plugin")
    success: bool = Field(..., description="Whether execution succeeded")
    output: Optional[Any] = Field(default=None, description="Structured output conforming to plugin output_schema")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Total execution latency in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution performance and tracing metadata")

    model_config = {"arbitrary_types_allowed": True}


class BasePlugin(ABC):
    """Abstract base contract for all modular plugins in Xeren."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """Plugin manifest describing identity, capabilities, and schemas."""
        pass

    @property
    def name(self) -> str:
        """Plugin identifier from manifest."""
        return self.manifest.name

    @property
    def version(self) -> str:
        """Plugin version string from manifest."""
        return self.manifest.version

    @property
    def description(self) -> str:
        """Plugin description from manifest."""
        return self.manifest.description

    @property
    def capabilities(self) -> List[str]:
        """Plugin capabilities from manifest."""
        return self.manifest.capabilities

    @property
    @abstractmethod
    def input_schema(self) -> Type[BaseModel]:
        """Pydantic model class defining the expected input schema."""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        """Pydantic model class defining the guaranteed output schema."""
        pass

    def validate_input(self, data: Any) -> BaseModel:
        """Validate raw or dictionary input against the plugin's input schema."""
        if isinstance(data, self.input_schema):
            return data
        if isinstance(data, dict):
            try:
                return self.input_schema.model_validate(data)
            except Exception as err:
                raise PluginValidationError(
                    f"Input data failed validation for plugin '{self.name}': {err}",
                    plugin_name=self.name,
                    raw_error=err,
                ) from err
        raise PluginValidationError(
            f"Input must be an instance of {self.input_schema.__name__} or a dict, got {type(data).__name__}",
            plugin_name=self.name,
        )

    def validate_output(self, data: Any) -> BaseModel:
        """Validate execution output against the plugin's output schema."""
        if isinstance(data, self.output_schema):
            return data
        if isinstance(data, dict):
            try:
                return self.output_schema.model_validate(data)
            except Exception as err:
                raise PluginValidationError(
                    f"Output data failed validation for plugin '{self.name}': {err}",
                    plugin_name=self.name,
                    raw_error=err,
                ) from err
        raise PluginValidationError(
            f"Output must be an instance of {self.output_schema.__name__} or a dict, got {type(data).__name__}",
            plugin_name=self.name,
        )

    @abstractmethod
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute the plugin with the provided input and context."""
        pass

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute the plugin with the provided input and context."""
        return await asyncio.to_thread(self.execute, input_data, context)

    def health_check(self) -> HealthCheckResult:
        """Check operational health and status information for this plugin."""
        start = time.perf_counter()
        return HealthCheckResult(
            status=PluginHealthStatus.HEALTHY,
            details={"name": self.name, "version": self.version},
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational health and status information."""
        return await asyncio.to_thread(self.health_check)

    def initialize(self) -> None:
        """Lifecycle hook invoked when the plugin is registered or initialized."""
        pass

    async def ainitialize(self) -> None:
        """Asynchronous lifecycle hook invoked on initialization."""
        await asyncio.to_thread(self.initialize)

    def shutdown(self) -> None:
        """Lifecycle hook invoked when the plugin is unregistered or system shuts down."""
        pass

    async def ashutdown(self) -> None:
        """Asynchronous lifecycle hook invoked on shutdown."""
        await asyncio.to_thread(self.shutdown)


__all__ = [
    "PluginCapability",
    "PluginHealthStatus",
    "HealthCheckResult",
    "PluginManifest",
    "PluginExecutionContext",
    "PluginExecutionResult",
    "BasePlugin",
]
