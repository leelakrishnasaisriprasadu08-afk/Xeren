"""Data transformation tool providing filtering, sorting, grouping, and aggregation."""

from collections import defaultdict
import logging
import statistics
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from xeren.plugins.data.schemas import (
    DataInput,
    DataOperation,
    DataResult,
    StructuredDataset,
    TransformConfig,
    TransformReport,
)

logger = logging.getLogger("xeren.plugins.data.tools.transformation")


class DataTransformationTool:
    """Applies declarative filters, sorting, grouping, aggregation, and projections."""

    def transform(
        self,
        dataset: StructuredDataset,
        config: TransformConfig,
    ) -> Tuple[StructuredDataset, TransformReport]:
        """Apply transformation pipeline to the dataset and return transformed dataset and report."""
        initial_rows = dataset.row_count
        current_columns = list(dataset.columns)
        current_rows: List[Dict[str, Any]] = [dict(r) for r in dataset.rows]
        transformations_applied: List[str] = []

        # 1. Apply Filters
        if config.filters:
            filtered_rows: List[Dict[str, Any]] = []
            for r in current_rows:
                if self._match_all_filters(r, config.filters):
                    filtered_rows.append(r)
            transformations_applied.append(f"filter (retained {len(filtered_rows)} of {len(current_rows)} rows)")
            current_rows = filtered_rows

        # 2. Apply Group By & Aggregation
        if config.group_by and config.aggregations:
            current_columns, current_rows = self._apply_group_by_aggregation(
                current_rows, config.group_by, config.aggregations
            )
            transformations_applied.append(
                f"group_by {config.group_by} with aggregations {config.aggregations} ({len(current_rows)} groups)"
            )
        elif config.aggregations and not config.group_by:
            # Single-row global aggregation
            current_columns, current_rows = self._apply_global_aggregation(
                current_rows, config.aggregations
            )
            transformations_applied.append(f"global aggregation {config.aggregations}")

        # 3. Apply Sorting
        if config.sort_by:
            sort_items: List[Tuple[str, bool]] = []
            for item in config.sort_by:
                if isinstance(item, str):
                    if item in current_columns:
                        sort_items.append((item, config.ascending))
                elif isinstance(item, dict):
                    col = item.get("column") or item.get("col") or ""
                    asc = item.get("ascending", config.ascending)
                    if col in current_columns:
                        sort_items.append((col, asc))

            if sort_items:
                for col, asc in reversed(sort_items):
                    def make_key(c: str) -> Callable[[Dict[str, Any]], Tuple[int, Any]]:
                        def _k(row: Dict[str, Any]) -> Tuple[int, Any]:
                            val = row.get(c)
                            if val is None:
                                return (1, "")
                            elif isinstance(val, (int, float)):
                                return (0, float(val))
                            else:
                                return (0, str(val))
                        return _k

                    current_rows.sort(key=make_key(col), reverse=not asc)
                transformations_applied.append(f"sort_by {sort_items}")

        # 4. Apply Column Selection / Projection
        if config.select_columns:
            selected = [c for c in config.select_columns if c in current_columns]
            if selected:
                current_columns = selected
                current_rows = [{col: r.get(col) for col in current_columns} for r in current_rows]
                transformations_applied.append(f"select_columns: {selected}")

        # 5. Apply Offset and Limit
        if config.offset is not None or config.limit is not None:
            start = config.offset or 0
            end = start + config.limit if config.limit is not None else len(current_rows)
            current_rows = current_rows[start:end]
            transformations_applied.append(f"slice: offset={config.offset}, limit={config.limit}")

        transformed_dataset = StructuredDataset(
            name=f"{dataset.name}_transformed",
            columns=current_columns,
            rows=current_rows,
            format=dataset.format,
        )

        report = TransformReport(
            initial_rows=initial_rows,
            transformed_rows=transformed_dataset.row_count,
            transformations_applied=transformations_applied,
        )

        return transformed_dataset, report

    def execute(self, input_data: DataInput) -> DataResult:
        """Execute transformation on a DataInput payload."""
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
            cfg = input_data.transform_config or TransformConfig()
            transformed_ds, report = self.transform(dataset, config=cfg)
            return DataResult(
                operation=DataOperation.TRANSFORM,
                success=True,
                dataset=transformed_ds,
                transformation=report,
                stats={"transformed_rows": transformed_ds.row_count},
            )
        except Exception as err:
            return DataResult(
                operation=DataOperation.TRANSFORM,
                success=False,
                error=str(err),
            )

    def _match_all_filters(self, row: Dict[str, Any], filters: Sequence[Dict[str, Any]]) -> bool:
        """Evaluate whether a row satisfies all filter specifications."""
        for f in filters:
            col = f.get("column")
            op = str(f.get("operator") or f.get("op") or "==").lower()
            val = f.get("value")

            if col not in row:
                return False

            row_val = row.get(col)

            if op == "is_null":
                if row_val is not None and row_val != "":
                    return False
            elif op == "not_null":
                if row_val is None or row_val == "":
                    return False
            elif op in ("==", "="):
                if row_val != val:
                    return False
            elif op in ("!=", "<>"):
                if row_val == val:
                    return False
            elif op == ">":
                if row_val is None or val is None or float(row_val) <= float(val):
                    return False
            elif op == ">=":
                if row_val is None or val is None or float(row_val) < float(val):
                    return False
            elif op == "<":
                if row_val is None or val is None or float(row_val) >= float(val):
                    return False
            elif op == "<=":
                if row_val is None or val is None or float(row_val) > float(val):
                    return False
            elif op == "in":
                if val is not None and row_val not in val:
                    return False
            elif op == "not_in":
                if val is not None and row_val in val:
                    return False
            elif op == "contains":
                if row_val is None or str(val).lower() not in str(row_val).lower():
                    return False

        return True

    def _apply_group_by_aggregation(
        self,
        rows: List[Dict[str, Any]],
        group_by: List[str],
        aggregations: Dict[str, str],
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Aggregate rows partitioned by group_by keys."""
        groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            group_key = tuple(r.get(col) for col in group_by)
            groups[group_key].append(r)

        result_columns = list(group_by)
        for col, agg_func in aggregations.items():
            result_columns.append(f"{col}_{agg_func.lower()}")

        result_rows: List[Dict[str, Any]] = []
        for group_key, group_rows in groups.items():
            row_dict: Dict[str, Any] = {}
            for col_idx, col_name in enumerate(group_by):
                row_dict[col_name] = group_key[col_idx]

            for col, agg_func in aggregations.items():
                agg_name = f"{col}_{agg_func.lower()}"
                values = [r.get(col) for r in group_rows if r.get(col) is not None and r.get(col) != ""]
                row_dict[agg_name] = self._compute_aggregation(values, agg_func)

            result_rows.append(row_dict)

        return result_columns, result_rows

    def _apply_global_aggregation(
        self,
        rows: List[Dict[str, Any]],
        aggregations: Dict[str, str],
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Aggregate all rows into a single summary record."""
        result_columns: List[str] = []
        result_row: Dict[str, Any] = {}

        for col, agg_func in aggregations.items():
            agg_name = f"{col}_{agg_func.lower()}"
            result_columns.append(agg_name)
            values = [r.get(col) for r in rows if r.get(col) is not None and r.get(col) != ""]
            result_row[agg_name] = self._compute_aggregation(values, agg_func)

        return result_columns, [result_row]

    def _compute_aggregation(self, values: Sequence[Any], func: str) -> Any:
        """Compute an individual aggregate metric."""
        func_lower = func.lower()
        if func_lower == "count":
            return len(values)
        if not values:
            return None

        numeric_vals = [float(v) for v in values if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "", 1).isdigit())]

        if func_lower in ("sum", "total"):
            return sum(numeric_vals) if numeric_vals else 0
        elif func_lower in ("avg", "mean", "average"):
            return round(statistics.mean(numeric_vals), 4) if numeric_vals else None
        elif func_lower == "min":
            return min(numeric_vals) if numeric_vals else min(values)
        elif func_lower == "max":
            return max(numeric_vals) if numeric_vals else max(values)
        elif func_lower == "first":
            return values[0]
        elif func_lower == "last":
            return values[-1]

        return len(values)


__all__ = ["DataTransformationTool"]
