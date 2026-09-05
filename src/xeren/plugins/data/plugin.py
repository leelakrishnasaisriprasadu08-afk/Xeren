"""Data Plugin implementation conforming to the Xeren BasePlugin contract."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Type, Union

from pydantic import BaseModel

from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.data.manifest import DATA_PLUGIN_MANIFEST
from xeren.plugins.data.registry import DataToolRegistry
from xeren.plugins.data.schemas import (
    AnalysisReport,
    ChartSpec,
    ChartType,
    CleaningRule,
    DataFormat,
    DataInput,
    DataOperation,
    DataResult,
    DataValidationRule,
    DataVerificationReport,
    InspectionReport,
    StructuredDataset,
    TransformConfig,
    VisualizationResult,
)
from xeren.plugins.data.workflow import DataWorkflow
from xeren.plugins.errors import PluginExecutionError

logger = logging.getLogger("xeren.plugins.data.plugin")


class DataPlugin(BasePlugin):
    """Modular Data Processing, Analysis, and Verification Plugin for Xeren Core."""

    def __init__(
        self,
        registry: Optional[DataToolRegistry] = None,
        workflow: Optional[DataWorkflow] = None,
    ) -> None:
        self.registry = registry or DataToolRegistry()
        self.workflow = workflow or DataWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return DATA_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return DataInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return DataResult

    # -------------------------------------------------------------------------
    # BasePlugin Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute a data operation."""
        start_time = time.perf_counter()
        try:
            validated_input: DataInput = self.validate_input(input_data)  # type: ignore
            result: DataResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "rows": result.dataset.row_count if result.dataset else 0,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("DataPlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"DataPlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute a data operation."""
        start_time = time.perf_counter()
        try:
            validated_input: DataInput = self.validate_input(input_data)  # type: ignore
            result: DataResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "rows": result.dataset.row_count if result.dataset else 0,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("DataPlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"DataPlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def ingest(
        self,
        data: Optional[Union[str, List[Dict[str, Any]], Dict[str, Any]]] = None,
        file_path: Optional[str] = None,
        format: Optional[Union[DataFormat, str]] = None,
        records: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> StructuredDataset:
        """Convenience method for data ingestion, returning the StructuredDataset."""
        inp = DataInput(
            operation=DataOperation.INGEST,
            data=data or records,
            records=records,
            file_path=file_path,
            format=format,
            metadata=kwargs,
        )
        res = self.workflow.execute_ingest(inp)
        if not res.success or res.dataset is None:
            raise PluginExecutionError(f"Ingestion failed: {res.error}", plugin_name=self.name)
        return res.dataset

    def inspect(
        self,
        dataset: Optional[Union[StructuredDataset, Any]] = None,
        data: Optional[Any] = None,
        file_path: Optional[str] = None,
        **kwargs: Any,
    ) -> InspectionReport:
        """Convenience method for data profiling and inspection."""
        target_ds = dataset if isinstance(dataset, StructuredDataset) else None
        raw_data = data if data is not None else (dataset if not isinstance(dataset, StructuredDataset) else None)
        inp = DataInput(
            operation=DataOperation.INSPECT,
            data=raw_data,
            dataset=target_ds,
            file_path=file_path,
            metadata=kwargs,
        )
        res = self.workflow.execute_inspect(inp)
        if not res.success or res.inspection is None:
            raise PluginExecutionError(f"Inspection failed: {res.error}", plugin_name=self.name)
        return res.inspection

    def clean(
        self,
        dataset: Optional[Union[StructuredDataset, Any]] = None,
        data: Optional[Any] = None,
        file_path: Optional[str] = None,
        rules: Optional[Union[CleaningRule, Sequence[CleaningRule]]] = None,
        **kwargs: Any,
    ) -> StructuredDataset:
        """Convenience method for data cleaning."""
        target_ds = dataset if isinstance(dataset, StructuredDataset) else None
        raw_data = data if data is not None else (dataset if not isinstance(dataset, StructuredDataset) else None)
        clean_rules: Optional[Union[CleaningRule, List[CleaningRule]]] = None
        if isinstance(rules, CleaningRule):
            clean_rules = rules
        elif rules is not None:
            clean_rules = list(rules)

        inp = DataInput(
            operation=DataOperation.CLEAN,
            data=raw_data,
            dataset=target_ds,
            file_path=file_path,
            cleaning_rules=clean_rules,
            metadata=kwargs,
        )
        res = self.workflow.execute_clean(inp)
        if not res.success or res.dataset is None:
            raise PluginExecutionError(f"Cleaning failed: {res.error}", plugin_name=self.name)
        return res.dataset

    def transform(
        self,
        dataset: Optional[Union[StructuredDataset, Any]] = None,
        data: Optional[Any] = None,
        file_path: Optional[str] = None,
        config: Optional[TransformConfig] = None,
        **kwargs: Any,
    ) -> StructuredDataset:
        """Convenience method for data transformation."""
        target_ds = dataset if isinstance(dataset, StructuredDataset) else None
        raw_data = data if data is not None else (dataset if not isinstance(dataset, StructuredDataset) else None)
        inp = DataInput(
            operation=DataOperation.TRANSFORM,
            data=raw_data,
            dataset=target_ds,
            file_path=file_path,
            transform_config=config,
            metadata=kwargs,
        )
        res = self.workflow.execute_transform(inp)
        if not res.success or res.dataset is None:
            raise PluginExecutionError(f"Transformation failed: {res.error}", plugin_name=self.name)
        return res.dataset

    def analyze(
        self,
        dataset: Optional[Union[StructuredDataset, Any]] = None,
        data: Optional[Any] = None,
        file_path: Optional[str] = None,
        columns: Optional[List[str]] = None,
        include_correlations: bool = False,
        **kwargs: Any,
    ) -> AnalysisReport:
        """Convenience method for statistical analysis."""
        target_ds = dataset if isinstance(dataset, StructuredDataset) else None
        raw_data = data if data is not None else (dataset if not isinstance(dataset, StructuredDataset) else None)
        inp = DataInput(
            operation=DataOperation.ANALYZE,
            data=raw_data,
            dataset=target_ds,
            file_path=file_path,
            analysis_columns=columns,
            include_correlations=include_correlations,
            metadata=kwargs,
        )
        res = self.workflow.execute_analyze(inp)
        if not res.success or res.analysis is None:
            raise PluginExecutionError(f"Analysis failed: {res.error}", plugin_name=self.name)
        return res.analysis

    def visualize(
        self,
        dataset: Optional[Union[StructuredDataset, Any]] = None,
        data: Optional[Any] = None,
        file_path: Optional[str] = None,
        spec: Optional[ChartSpec] = None,
        chart_type: Optional[Union[ChartType, str]] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs: Any,
    ) -> VisualizationResult:
        """Convenience method for chart generation and visualization."""
        target_ds = dataset if isinstance(dataset, StructuredDataset) else None
        raw_data = data if data is not None else (dataset if not isinstance(dataset, StructuredDataset) else None)
        c_type = ChartType(chart_type) if isinstance(chart_type, str) else chart_type
        inp = DataInput(
            operation=DataOperation.VISUALIZE,
            data=raw_data,
            dataset=target_ds,
            file_path=file_path,
            visualization_spec=spec,
            chart_type=c_type,
            chart_x=x,
            chart_y=y,
            metadata=kwargs,
        )
        res = self.workflow.execute_visualize(inp)
        if not res.success or res.visualization is None:
            raise PluginExecutionError(f"Visualization failed: {res.error}", plugin_name=self.name)
        return res.visualization

    def verify(
        self,
        dataset: Optional[Union[StructuredDataset, Any]] = None,
        data: Optional[Any] = None,
        file_path: Optional[str] = None,
        rules: Optional[List[DataValidationRule]] = None,
        **kwargs: Any,
    ) -> DataVerificationReport:
        """Convenience method for constraint validation."""
        target_ds = dataset if isinstance(dataset, StructuredDataset) else None
        raw_data = data if data is not None else (dataset if not isinstance(dataset, StructuredDataset) else None)
        inp = DataInput(
            operation=DataOperation.VERIFY,
            data=raw_data,
            dataset=target_ds,
            file_path=file_path,
            verification_rules=rules,
            metadata=kwargs,
        )
        res = self.workflow.execute_verify(inp)
        if res.verification is None:
            raise PluginExecutionError(f"Verification failed: {res.error}", plugin_name=self.name)
        return res.verification

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Check operational readiness of data tools and adapters."""
        start_time = time.perf_counter()
        if not self._initialized:
            return HealthCheckResult(
                status=PluginHealthStatus.UNHEALTHY,
                details={"initialized": False, "tools_ready": False},
                latency_ms=0.0,
                error="DataPlugin is not initialized",
            )
        adapters_count = len(self.registry.ingestion_tool.adapters)

        details = {
            "initialized": True,
            "adapters_registered": adapters_count,
            "max_bytes_limit": self.registry.ingestion_tool.max_bytes,
            "max_rows_limit": self.registry.ingestion_tool.max_rows,
            "registered_tools_count": 7,
            "tools_ready": True,
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


__all__ = ["DataPlugin"]
