"""Data visualization tool generating structured chart specifications and ASCII visual renders."""

from collections import Counter
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from xeren.plugins.data.schemas import (
    ChartSpec,
    ChartType,
    DataInput,
    DataOperation,
    DataResult,
    StructuredDataset,
    VisualizationResult,
)

logger = logging.getLogger("xeren.plugins.data.tools.visualization")


class DataVisualizationTool:
    """Renders structured visual specifications and ASCII representations for datasets."""

    def visualize(
        self,
        dataset: StructuredDataset,
        spec: Optional[ChartSpec] = None,
        chart_type: Optional[ChartType] = None,
        x_column: Optional[str] = None,
        y_column: Optional[str] = None,
        title: Optional[str] = None,
    ) -> VisualizationResult:
        """Generate visual chart specification and text rendering."""
        # 1. Resolve ChartSpec
        active_spec = spec or ChartSpec(
            chart_type=chart_type or ChartType.BAR,
            title=title or f"{dataset.name} Chart",
            x_column=x_column or (dataset.columns[0] if dataset.columns else None),
            y_column=y_column or (dataset.columns[1] if len(dataset.columns) > 1 else None),
        )

        labels: List[str] = []
        series_data: Dict[str, List[float]] = {}
        ascii_lines: List[str] = [f"=== {active_spec.title} ({active_spec.chart_type.value.upper()}) ==="]

        # 2. Compute visual representation based on chart type
        if active_spec.chart_type == ChartType.HISTOGRAM:
            labels, series_data, ascii_lines = self._build_histogram(dataset, active_spec)
        elif active_spec.chart_type in (ChartType.BAR, ChartType.PIE):
            labels, series_data, ascii_lines = self._build_categorical_chart(dataset, active_spec)
        elif active_spec.chart_type in (ChartType.SCATTER, ChartType.LINE):
            labels, series_data, ascii_lines = self._build_xy_chart(dataset, active_spec)

        active_spec.labels = labels
        active_spec.series = series_data

        structured = {
            "chart_type": active_spec.chart_type.value,
            "title": active_spec.title,
            "labels": labels,
            "series": series_data,
            "dataset_rows": dataset.row_count,
        }

        return VisualizationResult(
            chart_spec=active_spec,
            ascii_representation="\n".join(ascii_lines),
            structured_data=structured,
            format="json_chart_spec",
        )

    def execute(self, input_data: DataInput) -> DataResult:
        """Execute visualization on a DataInput payload."""
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
            spec = input_data.chart_spec or input_data.visualization_spec
            c_type = (
                ChartType(input_data.chart_type)
                if isinstance(input_data.chart_type, str)
                else input_data.chart_type
            )
            vis = self.visualize(
                dataset=dataset,
                spec=spec,
                chart_type=c_type,
                x_column=input_data.chart_x,
                y_column=input_data.chart_y,
            )
            return DataResult(
                operation=DataOperation.VISUALIZE,
                success=True,
                dataset=dataset,
                visualization=vis,
            )
        except Exception as err:
            return DataResult(
                operation=DataOperation.VISUALIZE,
                success=False,
                error=str(err),
            )

    def _build_histogram(
        self,
        dataset: StructuredDataset,
        spec: ChartSpec,
    ) -> Tuple[List[str], Dict[str, List[float]], List[str]]:
        """Compute bin ranges and counts for numeric histogram."""
        target_col = spec.x_column or (dataset.columns[0] if dataset.columns else "")
        raw_vals = dataset.get_column_values(target_col)
        nums: List[float] = []
        for v in raw_vals:
            try:
                if v is not None and v != "":
                    nums.append(float(v))
            except (ValueError, TypeError):
                pass

        if not nums:
            return [], {}, [f"No numeric values available in column '{target_col}' for histogram."]

        min_val = min(nums)
        max_val = max(nums)
        num_bins = min(spec.bins, max(2, len(nums) // 2))

        if min_val == max_val:
            bin_width = 1.0
            num_bins = 1
        else:
            bin_width = (max_val - min_val) / num_bins

        bin_counts = [0] * num_bins
        labels = []
        for i in range(num_bins):
            b_start = round(min_val + i * bin_width, 2)
            b_end = round(b_start + bin_width, 2)
            labels.append(f"[{b_start:.1f} - {b_end:.1f}]")

        for n in nums:
            if n == max_val and num_bins > 1:
                idx = num_bins - 1
            else:
                idx = int((n - min_val) / bin_width) if bin_width > 0 else 0
                idx = max(0, min(idx, num_bins - 1))
            bin_counts[idx] += 1

        ascii_lines = [f"=== {spec.title} ===", f"Histogram for '{target_col}':"]
        max_count = max(bin_counts) if bin_counts else 1
        bar_scale = 30 / max_count if max_count > 0 else 1

        for label, count in zip(labels, bin_counts):
            bar = "#" * max(1, int(count * bar_scale))
            ascii_lines.append(f"  {label:<16} | {bar} ({count})")

        return labels, {"counts": [float(c) for c in bin_counts]}, ascii_lines

    def _build_categorical_chart(
        self,
        dataset: StructuredDataset,
        spec: ChartSpec,
    ) -> Tuple[List[str], Dict[str, List[float]], List[str]]:
        """Compute category totals for Bar or Pie charts."""
        x_col = spec.x_column or (dataset.columns[0] if dataset.columns else "")
        y_col = spec.y_column

        labels: List[str] = []
        values: List[float] = []

        if y_col and y_col in dataset.columns and y_col != x_col:
            # Aggregate y_col by x_col
            totals: Dict[str, float] = {}
            for r in dataset.rows:
                cat = str(r.get(x_col, "Unknown"))
                y_val = r.get(y_col)
                try:
                    num_val = float(y_val) if y_val is not None else 0.0
                except (ValueError, TypeError):
                    num_val = 0.0
                totals[cat] = totals.get(cat, 0.0) + num_val

            for cat, tot in sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]:
                labels.append(cat)
                values.append(round(tot, 2))
        else:
            # Frequency count of x_col
            counts = Counter(str(r.get(x_col, "Unknown")) for r in dataset.rows)
            for cat, cnt in counts.most_common(10):
                labels.append(cat)
                values.append(float(cnt))

        ascii_lines = [f"=== {spec.title} ===", f"Chart for '{x_col}':"]
        max_val = max(values) if values else 1.0
        bar_scale = 30 / max_val if max_val > 0 else 1.0

        for label, val in zip(labels, values):
            bar = "#" * max(1, int(val * bar_scale))
            ascii_lines.append(f"  {label[:15]:<16} | {bar} ({val})")

        return labels, {"values": values}, ascii_lines

    def _build_xy_chart(
        self,
        dataset: StructuredDataset,
        spec: ChartSpec,
    ) -> Tuple[List[str], Dict[str, List[float]], List[str]]:
        """Compute point series for Scatter or Line charts."""
        x_col = spec.x_column or (dataset.columns[0] if dataset.columns else "")
        y_col = spec.y_column or (dataset.columns[1] if len(dataset.columns) > 1 else x_col)

        xs: List[float] = []
        ys: List[float] = []
        labels: List[str] = []

        for idx, r in enumerate(dataset.rows[:50]):  # sample first 50 points
            try:
                x_val = float(r.get(x_col, 0.0))
                y_val = float(r.get(y_col, 0.0))
                xs.append(x_val)
                ys.append(y_val)
                labels.append(f"Point {idx + 1}")
            except (ValueError, TypeError):
                continue

        ascii_lines = [
            f"{spec.chart_type.value.capitalize()} plot ({x_col} vs {y_col}):",
            f"  Rendered {len(xs)} data points.",
        ]
        if xs and ys:
            ascii_lines.append(f"  X Range: [{min(xs):.2f}, {max(xs):.2f}]")
            ascii_lines.append(f"  Y Range: [{min(ys):.2f}, {max(ys):.2f}]")

        return labels, {"x": xs, "y": ys}, ascii_lines


__all__ = ["DataVisualizationTool"]
