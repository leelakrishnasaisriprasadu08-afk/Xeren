"""Data workflow orchestrating dataset ingestion, inspection, cleaning, transformation, analysis, visualization, and verification."""

import asyncio
import logging
import time
from typing import Optional

from xeren.plugins.data.registry import DataToolRegistry
from xeren.plugins.data.schemas import (
    ChartType,
    DataInput,
    DataOperation,
    DataResult,
    StructuredDataset,
    TransformConfig,
)
from xeren.plugins.data.tools.ingestion import DataIngestionError

logger = logging.getLogger("xeren.plugins.data.workflow")


class DataWorkflow:
    """Orchestrates modular data lifecycle operations."""

    def __init__(self, registry: Optional[DataToolRegistry] = None) -> None:
        self.registry = registry or DataToolRegistry()

    def _resolve_dataset(self, input_data: DataInput) -> StructuredDataset:
        """Resolve or ingest the active dataset from inputs."""
        return self.registry.ingestion_tool.ingest(
            data=input_data.data,
            file_path=input_data.file_path,
            dataset=input_data.dataset,
            format_hint=input_data.format,
            options=input_data.metadata,
        )

    # -------------------------------------------------------------------------
    # Handlers
    # -------------------------------------------------------------------------
    def execute_ingest(self, input_data: DataInput) -> DataResult:
        """Ingest and profile a dataset."""
        start_time = time.perf_counter()
        try:
            dataset = self._resolve_dataset(input_data)
            inspection = self.registry.inspection_tool.inspect(dataset)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DataResult(
                operation=DataOperation.INGEST,
                success=True,
                dataset=dataset,
                inspection=inspection,
                stats={
                    "latency_ms": latency_ms,
                    "rows": dataset.row_count,
                    "columns": dataset.column_count,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Data ingest failed: %s", err)
            return DataResult(
                operation=DataOperation.INGEST,
                success=False,
                error=str(err),
                stats={"latency_ms": latency_ms},
            )

    def execute_inspect(self, input_data: DataInput) -> DataResult:
        """Profile dataset structure, types, missing values, and duplicates."""
        start_time = time.perf_counter()
        try:
            dataset = self._resolve_dataset(input_data)
            inspection = self.registry.inspection_tool.inspect(dataset)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DataResult(
                operation=DataOperation.INSPECT,
                success=True,
                dataset=dataset,
                inspection=inspection,
                stats={"latency_ms": latency_ms, "rows": dataset.row_count},
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Data inspect failed: %s", err)
            return DataResult(
                operation=DataOperation.INSPECT,
                success=False,
                error=str(err),
                stats={"latency_ms": latency_ms},
            )

    def execute_clean(self, input_data: DataInput) -> DataResult:
        """Clean dataset by applying deduplication, imputation, and column transformations."""
        start_time = time.perf_counter()
        try:
            dataset = self._resolve_dataset(input_data)
            cleaned_ds, cleaning_report = self.registry.cleaning_tool.clean(
                dataset, rules=input_data.cleaning_rules
            )
            inspection = self.registry.inspection_tool.inspect(cleaned_ds)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DataResult(
                operation=DataOperation.CLEAN,
                success=True,
                dataset=cleaned_ds,
                cleaning=cleaning_report,
                inspection=inspection,
                stats={
                    "latency_ms": latency_ms,
                    "initial_rows": cleaning_report.initial_rows,
                    "cleaned_rows": cleaning_report.cleaned_rows,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Data clean failed: %s", err)
            return DataResult(
                operation=DataOperation.CLEAN,
                success=False,
                error=str(err),
                stats={"latency_ms": latency_ms},
            )

    def execute_transform(self, input_data: DataInput) -> DataResult:
        """Apply filtering, sorting, grouping, aggregations, and projections."""
        start_time = time.perf_counter()
        try:
            dataset = self._resolve_dataset(input_data)
            config = input_data.transform_config or TransformConfig()
            transformed_ds, transform_report = self.registry.transformation_tool.transform(dataset, config)
            inspection = self.registry.inspection_tool.inspect(transformed_ds)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DataResult(
                operation=DataOperation.TRANSFORM,
                success=True,
                dataset=transformed_ds,
                transformation=transform_report,
                inspection=inspection,
                stats={
                    "latency_ms": latency_ms,
                    "transformed_rows": transformed_ds.row_count,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Data transform failed: %s", err)
            return DataResult(
                operation=DataOperation.TRANSFORM,
                success=False,
                error=str(err),
                stats={"latency_ms": latency_ms},
            )

    def execute_analyze(self, input_data: DataInput) -> DataResult:
        """Compute summary statistics, distributions, and correlation matrices."""
        start_time = time.perf_counter()
        try:
            dataset = self._resolve_dataset(input_data)
            analysis_report = self.registry.analysis_tool.analyze(
                dataset=dataset,
                columns=input_data.analysis_columns,
                include_correlations=input_data.include_correlations,
            )
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DataResult(
                operation=DataOperation.ANALYZE,
                success=True,
                dataset=dataset,
                analysis=analysis_report,
                stats={"latency_ms": latency_ms, "analyzed_columns": len(analysis_report.statistics)},
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Data analyze failed: %s", err)
            return DataResult(
                operation=DataOperation.ANALYZE,
                success=False,
                error=str(err),
                stats={"latency_ms": latency_ms},
            )

    def execute_visualize(self, input_data: DataInput) -> DataResult:
        """Render chart specifications and ASCII visual representations."""
        start_time = time.perf_counter()
        try:
            dataset = self._resolve_dataset(input_data)
            c_type = (
                ChartType(input_data.chart_type)
                if isinstance(input_data.chart_type, str)
                else input_data.chart_type
            )
            vis_result = self.registry.visualization_tool.visualize(
                dataset=dataset,
                spec=input_data.visualization_spec,
                chart_type=c_type,
                x_column=input_data.chart_x,
                y_column=input_data.chart_y,
            )
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DataResult(
                operation=DataOperation.VISUALIZE,
                success=True,
                dataset=dataset,
                visualization=vis_result,
                stats={"latency_ms": latency_ms},
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Data visualize failed: %s", err)
            return DataResult(
                operation=DataOperation.VISUALIZE,
                success=False,
                error=str(err),
                stats={"latency_ms": latency_ms},
            )

    def execute_verify(self, input_data: DataInput) -> DataResult:
        """Verify data integrity against declarative constraints and rules."""
        start_time = time.perf_counter()
        try:
            dataset = self._resolve_dataset(input_data)
            rules = input_data.verification_rules or []
            verification_report = self.registry.verification_tool.verify(dataset, rules)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DataResult(
                operation=DataOperation.VERIFY,
                success=True,
                dataset=dataset,
                verification=verification_report,
                stats={
                    "latency_ms": latency_ms,
                    "rules_checked": verification_report.rules_checked,
                    "rules_passed": verification_report.rules_passed,
                },
                error=None if verification_report.is_valid else verification_report.summary,
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Data verify failed: %s", err)
            return DataResult(
                operation=DataOperation.VERIFY,
                success=False,
                error=str(err),
                stats={"latency_ms": latency_ms},
            )

    # -------------------------------------------------------------------------
    # Main Dispatcher
    # -------------------------------------------------------------------------
    def run(self, input_data: DataInput) -> DataResult:
        """Synchronously dispatch data operation."""
        op = input_data.operation
        if op == DataOperation.INGEST:
            return self.execute_ingest(input_data)
        elif op == DataOperation.INSPECT:
            return self.execute_inspect(input_data)
        elif op == DataOperation.CLEAN:
            return self.execute_clean(input_data)
        elif op == DataOperation.TRANSFORM:
            return self.execute_transform(input_data)
        elif op == DataOperation.ANALYZE:
            return self.execute_analyze(input_data)
        elif op == DataOperation.VISUALIZE:
            return self.execute_visualize(input_data)
        elif op == DataOperation.VERIFY:
            return self.execute_verify(input_data)
        return self.execute_inspect(input_data)

    async def arun(self, input_data: DataInput) -> DataResult:
        """Asynchronously dispatch data operation."""
        return await asyncio.to_thread(self.run, input_data)


__all__ = ["DataWorkflow"]
