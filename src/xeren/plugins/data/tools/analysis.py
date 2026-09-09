"""Data statistical analysis and correlation tool."""

from collections import Counter
import logging
import math
import statistics
from typing import Any, Dict, List, Optional, Sequence, Union

from xeren.plugins.data.schemas import (
    AnalysisReport,
    ColumnStatistics,
    CorrelationMatrix,
    DataInput,
    DataOperation,
    DataResult,
    StructuredDataset,
)

logger = logging.getLogger("xeren.plugins.data.tools.analysis")


class StatsList(list):
    """List of ColumnStatistics supporting dict-style key access by column name."""

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            for s in self:
                if getattr(s, "column", None) == item or getattr(s, "column_name", None) == item:
                    return s
            raise KeyError(f"Column '{item}' not found in statistics")
        return super().__getitem__(item)


class MatrixGrid(list):
    """2D correlation grid supporting both [i][j] index access and [col_a][col_b] dict-style access."""

    def __init__(self, grid: List[List[float]], columns: List[str]):
        super().__init__(grid)
        self.columns = columns

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            if item not in self.columns:
                raise KeyError(f"Column '{item}' not in correlation matrix")
            idx = self.columns.index(item)
            row = super().__getitem__(idx)
            return {self.columns[k]: row[k] for k in range(len(self.columns))}
        return super().__getitem__(item)


class DataAnalysisTool:
    """Computes descriptive statistics, distributions, and correlation matrices."""

    def analyze(
        self,
        dataset: StructuredDataset,
        columns: Optional[List[str]] = None,
        include_correlations: bool = False,
    ) -> AnalysisReport:
        """Run statistical analysis across dataset columns."""
        target_cols = [c for c in (columns or dataset.columns) if c in dataset.columns]
        stats_map: Dict[str, ColumnStatistics] = {}
        numeric_cols: List[str] = []

        for col in target_cols:
            raw_vals = dataset.get_column_values(col)
            null_count = sum(1 for v in raw_vals if v is None or v == "")
            non_null = [v for v in raw_vals if v is not None and v != ""]
            count = len(non_null)

            # Check if column is numeric
            numeric_vals: List[float] = []
            for v in non_null:
                if isinstance(v, (int, float)):
                    numeric_vals.append(float(v))
                elif isinstance(v, str):
                    try:
                        numeric_vals.append(float(v))
                    except ValueError:
                        break

            if len(numeric_vals) == count and count > 0:
                numeric_cols.append(col)
                stats = self._compute_numeric_stats(col, count, null_count, numeric_vals)
            else:
                stats = self._compute_categorical_stats(col, count, null_count, non_null)

            stats_map[col] = stats

        # Pearson correlation analysis
        correlation_matrix: Optional[CorrelationMatrix] = None
        if include_correlations and len(numeric_cols) >= 2:
            correlation_matrix = self._compute_correlation_matrix(dataset, numeric_cols)

        # Formulate reasoning summary
        summary = self._generate_summary(dataset, stats_map, correlation_matrix)

        return AnalysisReport(
            total_records=dataset.row_count,
            statistics=StatsList(list(stats_map.values())),
            correlations=correlation_matrix,
            summary=summary,
        )

    def execute(self, input_data: DataInput) -> DataResult:
        """Execute statistical analysis on a DataInput payload."""
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
            report = self.analyze(
                dataset=dataset,
                columns=input_data.analysis_columns,
                include_correlations=input_data.include_correlations or True,
            )
            return DataResult(
                operation=DataOperation.ANALYZE,
                success=True,
                dataset=dataset,
                analysis=report,
                stats={"analyzed_columns": len(report.statistics)},
            )
        except Exception as err:
            return DataResult(
                operation=DataOperation.ANALYZE,
                success=False,
                error=str(err),
            )

    def _compute_numeric_stats(
        self,
        col: str,
        count: int,
        null_count: int,
        values: List[float],
    ) -> ColumnStatistics:
        """Calculate mean, standard deviation, quartiles, and range for numeric columns."""
        values.sort()
        mean_val = round(statistics.mean(values), 4)
        std_val = round(statistics.stdev(values), 4) if len(values) > 1 else 0.0
        min_val = values[0]
        max_val = values[-1]
        median_val = round(statistics.median(values), 4)

        # Quartiles
        q25 = self._percentile(values, 0.25)
        q75 = self._percentile(values, 0.75)

        # Mode
        counts = Counter(values)
        mode_val = counts.most_common(1)[0][0]

        return ColumnStatistics(
            column=col,
            count=count,
            null_count=null_count,
            mean=mean_val,
            std_dev=std_val,
            min=min_val,
            q25=q25,
            median=median_val,
            q75=q75,
            max=max_val,
            mode=mode_val,
        )

    def _compute_categorical_stats(
        self,
        col: str,
        count: int,
        null_count: int,
        values: Sequence[Any],
    ) -> ColumnStatistics:
        """Compute frequencies and top values for categorical columns."""
        str_vals = [str(v) for v in values]
        counts = Counter(str_vals)
        top_items = dict(counts.most_common(5))
        mode_val = counts.most_common(1)[0][0] if str_vals else None

        return ColumnStatistics(
            column=col,
            count=count,
            null_count=null_count,
            mode=mode_val,
            top_values=top_items,
        )

    @staticmethod
    def _percentile(sorted_data: List[float], p: float) -> float:
        """Compute percentile value from sorted numeric array."""
        if not sorted_data:
            return 0.0
        n = len(sorted_data)
        idx = (n - 1) * p
        lower = int(math.floor(idx))
        upper = int(math.ceil(idx))
        if lower == upper:
            return sorted_data[lower]
        weight = idx - lower
        return round(sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight, 4)

    def _compute_correlation_matrix(
        self,
        dataset: StructuredDataset,
        numeric_cols: List[str],
    ) -> CorrelationMatrix:
        """Compute pairwise Pearson correlation coefficients in a 2D matrix."""
        # Extract aligned numeric arrays
        col_arrays: Dict[str, List[float]] = {}
        for c in numeric_cols:
            vals = []
            for r in dataset.rows:
                v = r.get(c)
                try:
                    vals.append(float(v) if v is not None else float("nan"))
                except (ValueError, TypeError):
                    vals.append(float("nan"))
            col_arrays[c] = vals

        n = len(numeric_cols)
        grid: List[List[float]] = [[0.0] * n for _ in range(n)]

        for i, col_a in enumerate(numeric_cols):
            grid[i][i] = 1.0
            for j in range(i + 1, n):
                col_b = numeric_cols[j]
                r = self._pearson(col_arrays[col_a], col_arrays[col_b])
                grid[i][j] = r
                grid[j][i] = r

        return CorrelationMatrix(columns=numeric_cols, matrix=MatrixGrid(grid, numeric_cols))

    @staticmethod
    def _pearson(x: Sequence[float], y: Sequence[float]) -> float:
        """Calculate Pearson r correlation ignoring NaN pairs."""
        valid_pairs = [(xi, yi) for xi, yi in zip(x, y) if not math.isnan(xi) and not math.isnan(yi)]
        n = len(valid_pairs)
        if n < 2:
            return 0.0

        xs = [p[0] for p in valid_pairs]
        ys = [p[1] for p in valid_pairs]

        mean_x = statistics.mean(xs)
        mean_y = statistics.mean(ys)

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in valid_pairs)
        denom_x = sum((xi - mean_x) ** 2 for xi in xs)
        denom_y = sum((yi - mean_y) ** 2 for yi in ys)

        if denom_x <= 0 or denom_y <= 0:
            return 0.0

        return round(numerator / math.sqrt(denom_x * denom_y), 4)

    def _generate_summary(
        self,
        dataset: StructuredDataset,
        stats: Dict[str, ColumnStatistics],
        correlations: Optional[CorrelationMatrix],
    ) -> str:
        """Formulate a concise natural-language reasoning summary."""
        lines = [
            f"# Data Analysis Summary\nDataset '{dataset.name}' profile: {dataset.row_count} rows, {dataset.column_count} columns."
        ]

        numeric_summaries = []
        cat_summaries = []
        for col_name, s in stats.items():
            if s.mean is not None:
                numeric_summaries.append(
                    f"- {col_name}: mean={s.mean}, std={s.std_dev}, min={s.min}, max={s.max}, nulls={s.null_count}"
                )
            elif s.top_values:
                top_str = ", ".join(f"{k}: {v}" for k, v in list(s.top_values.items())[:3])
                cat_summaries.append(f"- {col_name}: top categories ({top_str}), nulls={s.null_count}")

        if numeric_summaries:
            lines.append("\nNumeric Attributes:")
            lines.extend(numeric_summaries)

        if cat_summaries:
            lines.append("\nCategorical Attributes:")
            lines.extend(cat_summaries)

        if correlations and correlations.matrix:
            strong_pairs = []
            cols = correlations.columns
            grid = correlations.matrix
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    col_a = cols[i]
                    col_b = cols[j]
                    if isinstance(grid, list):
                        r = grid[i][j]
                    else:
                        r = grid.get(col_a, {}).get(col_b, 0.0)
                    if abs(r) >= 0.5:
                        strong_pairs.append(f"{col_a} & {col_b} (r={r})")
            if strong_pairs:
                lines.append(f"\nStrong Correlations: {', '.join(strong_pairs)}")

        return "\n".join(lines)


__all__ = ["DataAnalysisTool", "StatsList", "MatrixGrid"]
