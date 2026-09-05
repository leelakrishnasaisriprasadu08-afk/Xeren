"""Data inspection and profiling tool."""

import json
import logging
from typing import Any, Dict, List, Sequence, Set, Tuple

from xeren.plugins.data.schemas import (
    ColumnInfo,
    ColumnType,
    DataInput,
    DataOperation,
    DataResult,
    InspectionReport,
    StructuredDataset,
)
from xeren.plugins.data.tools.ingestion import infer_scalar_type

logger = logging.getLogger("xeren.plugins.data.tools.inspection")


class DataInspectionTool:
    """Inspects structural properties, columns, data types, missing values, and duplicates."""

    def inspect(self, dataset: StructuredDataset) -> InspectionReport:
        """Analyze a StructuredDataset and generate a comprehensive InspectionReport."""
        row_count = dataset.row_count
        column_count = dataset.column_count

        columns_info: List[ColumnInfo] = []
        total_missing = 0

        for col in dataset.columns:
            values = dataset.get_column_values(col)
            null_count = sum(1 for v in values if v is None or v == "")
            total_missing += null_count

            non_null_values = [v for v in values if v is not None and v != ""]
            unique_count = len(set(str(v) for v in non_null_values))

            # Infer dominant column type
            inferred_type = self._infer_column_type(non_null_values)

            # Extract diverse sample values (up to 5)
            sample_values: List[Any] = []
            seen_samples: Set[str] = set()
            for v in non_null_values:
                s_str = str(v)
                if s_str not in seen_samples:
                    seen_samples.add(s_str)
                    sample_values.append(v)
                if len(sample_values) >= 5:
                    break

            columns_info.append(
                ColumnInfo(
                    name=col,
                    data_type=inferred_type,
                    total_count=row_count,
                    null_count=null_count,
                    unique_count=unique_count,
                    sample_values=sample_values,
                )
            )

        # Duplicate row detection
        duplicate_count = self._count_duplicate_rows(dataset.rows)

        # Memory estimation
        memory_bytes = self._estimate_memory_bytes(dataset)

        return InspectionReport(
            row_count=row_count,
            column_count=column_count,
            columns=columns_info,
            missing_cell_count=total_missing,
            duplicate_row_count=duplicate_count,
            memory_estimate_bytes=memory_bytes,
        )

    def execute(self, input_data: DataInput) -> DataResult:
        """Execute inspection on a DataInput payload."""
        try:
            dataset = input_data.dataset
            if dataset is None:
                from xeren.plugins.data.tools.ingestion import DataIngestionTool
                dataset = DataIngestionTool().ingest(
                    data=input_data.data or input_data.records,
                    file_path=input_data.file_path,
                    format_hint=input_data.format,
                    options=input_data.metadata,
                )
            report = self.inspect(dataset)
            return DataResult(
                operation=DataOperation.INSPECT,
                success=True,
                dataset=dataset,
                inspection=report,
                stats={"rows": dataset.row_count, "columns": dataset.column_count},
            )
        except Exception as err:
            return DataResult(
                operation=DataOperation.INSPECT,
                success=False,
                error=str(err),
            )

    def _infer_column_type(self, values: Sequence[Any]) -> ColumnType:
        """Infer aggregate column type from non-null values."""
        if not values:
            return ColumnType.UNKNOWN

        type_counts: Dict[ColumnType, int] = {}
        for v in values:
            t = infer_scalar_type(v)
            type_counts[t] = type_counts.get(t, 0) + 1

        # If all values are integer, return INTEGER
        if type_counts.get(ColumnType.INTEGER, 0) == len(values):
            return ColumnType.INTEGER

        # If all values are float or integer, return FLOAT
        num_numeric = type_counts.get(ColumnType.INTEGER, 0) + type_counts.get(ColumnType.FLOAT, 0)
        if num_numeric == len(values):
            return ColumnType.FLOAT

        # If all are boolean
        if type_counts.get(ColumnType.BOOLEAN, 0) == len(values):
            return ColumnType.BOOLEAN

        # If all are datetime
        if type_counts.get(ColumnType.DATETIME, 0) == len(values):
            return ColumnType.DATETIME

        # Default to dominant type or STRING
        dominant_type = max(type_counts, key=type_counts.get)  # type: ignore
        return dominant_type if dominant_type != ColumnType.UNKNOWN else ColumnType.STRING

    def _count_duplicate_rows(self, rows: List[Dict[str, Any]]) -> int:
        """Count identical row entries."""
        if not rows:
            return 0
        seen_hashes: Set[int] = set()
        duplicates = 0
        for r in rows:
            # Deterministic serialization for hashing
            row_key = hash(tuple(sorted((k, str(v)) for k, v in r.items())))
            if row_key in seen_hashes:
                duplicates += 1
            else:
                seen_hashes.add(row_key)
        return duplicates

    def _estimate_memory_bytes(self, dataset: StructuredDataset) -> int:
        """Estimate in-memory byte footprint."""
        approx = 0
        for col in dataset.columns:
            approx += len(col.encode("utf-8")) + 64
        for r in dataset.rows:
            for v in r.values():
                if v is None:
                    approx += 16
                elif isinstance(v, (int, float, bool)):
                    approx += 24
                else:
                    approx += len(str(v).encode("utf-8")) + 48
        return approx


__all__ = ["DataInspectionTool"]
