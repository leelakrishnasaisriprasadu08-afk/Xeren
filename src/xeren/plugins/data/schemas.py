"""Data schemas for Xeren Data Plugin (Plugin #5).

Defines core tabular data models, operation specifications, inspection profiles,
cleaning rules, transformation pipelines, analysis metrics, visualization specs,
and integrity verification reports.
"""

from enum import Enum
import io
import json
import csv
from typing import Any, Dict, List, Optional, Sequence, Union
from pydantic import BaseModel, Field, model_validator


class CountInt(int):
    """Integer subclass that can also be called as a method returning itself."""

    def __call__(self) -> int:
        return int(self)


class DataOperation(str, Enum):
    """Supported data plugin operational modes."""

    INGEST = "ingest"
    INSPECT = "inspect"
    CLEAN = "clean"
    TRANSFORM = "transform"
    ANALYZE = "analyze"
    VISUALIZE = "visualize"
    VERIFY = "verify"


class DataFormat(str, Enum):
    """Supported tabular data file and serialization formats."""

    CSV = "csv"
    JSON = "json"
    DICT = "dict"
    RECORDS = "records"


class ColumnType(str, Enum):
    """Inferred and validated column scalar types."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    OBJECT = "object"
    UNKNOWN = "unknown"


# -----------------------------------------------------------------------------
# Inspection Schemas
# -----------------------------------------------------------------------------
class ColumnInfo(BaseModel):
    """Detailed structural metadata and profile for a dataset column."""

    name: str = Field(..., description="Column header name")
    data_type: ColumnType = Field(default=ColumnType.UNKNOWN, description="Inferred scalar type")
    total_count: int = Field(default=0, ge=0, description="Total values evaluated")
    null_count: int = Field(default=0, ge=0, description="Count of missing or null cells")
    unique_count: int = Field(default=0, ge=0, description="Count of distinct values")
    sample_values: List[Any] = Field(default_factory=list, description="Diverse representative samples")

    @property
    def inferred_type(self) -> ColumnType:
        return self.data_type

    @property
    def distinct_count(self) -> int:
        return self.unique_count

    @property
    def null_percentage(self) -> float:
        return (self.null_count / self.total_count * 100.0) if self.total_count > 0 else 0.0


class InspectionReport(BaseModel):
    """Comprehensive structural and statistical profile of a dataset."""

    row_count: int = Field(default=0, ge=0, description="Total rows in dataset")
    column_count: int = Field(default=0, ge=0, description="Total columns in dataset")
    columns: List[ColumnInfo] = Field(default_factory=list, description="Per-column profiles")
    missing_cell_count: int = Field(default=0, ge=0, description="Total null or empty cells")
    duplicate_row_count: int = Field(default=0, ge=0, description="Count of duplicate row records")
    memory_estimate_bytes: int = Field(default=0, ge=0, description="Estimated in-memory footprint")

    @property
    def duplicate_rows(self) -> int:
        return self.duplicate_row_count


# -----------------------------------------------------------------------------
# Cleaning Schemas
# -----------------------------------------------------------------------------
class CleaningRule(BaseModel):
    """Specification of cleaning operations to execute on a dataset."""

    rule_type: Optional[str] = Field(default=None, description="Granular rule type (e.g. drop_duplicates, trim_strings)")
    column: Optional[str] = Field(default=None, description="Target column if applicable")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific parameters")

    drop_duplicates: bool = Field(default=True, description="Whether to drop duplicate rows")
    fill_missing: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Column-specific fill values or imputation strategies ('mean', 'median', 'mode', 'constant')",
    )
    drop_missing_columns: Optional[List[str]] = Field(
        default=None,
        description="Drop rows where any of these columns have null values",
    )
    drop_all_missing_rows: bool = Field(
        default=False,
        description="Drop rows where all values are null",
    )
    strip_strings: bool = Field(
        default=True,
        description="Trim whitespace from string values",
    )
    column_renames: Optional[Dict[str, str]] = Field(
        default=None,
        description="Mapping from old column name to new column name",
    )
    cast_types: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Explicit type casting targets per column",
    )


class CleaningReport(BaseModel):
    """Summary of cleaning transformations applied to a dataset."""

    initial_rows: int = Field(default=0, ge=0)
    cleaned_rows: int = Field(default=0, ge=0)
    duplicates_removed: int = Field(default=0, ge=0)
    missing_imputed: int = Field(default=0, ge=0)
    missing_dropped: int = Field(default=0, ge=0)
    operations_applied: List[str] = Field(default_factory=list)

    rows_removed: Optional[int] = None
    final_rows: Optional[int] = None
    actions_taken: List[str] = Field(default_factory=list)
    columns_modified: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_cleaning_fields(self) -> "CleaningReport":
        if self.final_rows is None:
            self.final_rows = self.cleaned_rows
        elif self.cleaned_rows == 0 and self.final_rows is not None:
            self.cleaned_rows = self.final_rows

        if self.rows_removed is None:
            self.rows_removed = self.duplicates_removed + self.missing_dropped

        if not self.actions_taken and self.operations_applied:
            self.actions_taken = list(self.operations_applied)
        elif self.actions_taken and not self.operations_applied:
            self.operations_applied = list(self.actions_taken)
        return self


# -----------------------------------------------------------------------------
# Transformation Schemas
# -----------------------------------------------------------------------------
class TransformConfig(BaseModel):
    """Configuration for data filtering, sorting, grouping, and aggregation."""

    filters: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Declarative filters: [{'column': 'col', 'operator': '>=', 'value': 100}]",
    )
    sort_by: Optional[Union[List[str], List[Dict[str, Any]]]] = Field(
        default=None,
        description="Sort columns, e.g. ['col1'] or [{'column': 'col1', 'ascending': False}]",
    )
    ascending: bool = Field(default=True, description="Default sort order if not specified per-column")
    group_by: Optional[List[str]] = Field(
        default=None,
        description="Columns to group by for aggregation",
    )
    aggregations: Optional[Dict[str, str]] = Field(
        default=None,
        description="Column to aggregation function ('sum', 'avg', 'min', 'max', 'count')",
    )
    select_columns: Optional[List[str]] = Field(
        default=None,
        description="Subset of columns to retain",
    )
    limit: Optional[int] = Field(default=None, ge=1, description="Max rows to return")
    offset: Optional[int] = Field(default=None, ge=0, description="Row offset for pagination")


class TransformReport(BaseModel):
    """Summary of data transformations applied."""

    initial_rows: int = Field(default=0, ge=0)
    transformed_rows: int = Field(default=0, ge=0)
    transformations_applied: List[str] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Analysis Schemas
# -----------------------------------------------------------------------------
class ColumnStatistics(BaseModel):
    """Statistical summary metrics for a numerical or categorical column."""

    column: str = Field(...)
    count: int = Field(default=0, ge=0)
    null_count: int = Field(default=0, ge=0)
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    min: Optional[float] = None
    q25: Optional[float] = None
    median: Optional[float] = None
    q75: Optional[float] = None
    max: Optional[float] = None
    mode: Optional[Any] = None
    top_values: Optional[Dict[str, int]] = None

    @property
    def column_name(self) -> str:
        return self.column

    @property
    def min_value(self) -> Optional[float]:
        return self.min

    @property
    def max_value(self) -> Optional[float]:
        return self.max


class CorrelationMatrix(BaseModel):
    """Pairwise Pearson correlation matrix for numeric columns."""

    columns: List[str] = Field(default_factory=list)
    matrix: List[List[float]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class AnalysisReport(BaseModel):
    """Comprehensive statistical and analytical report for a dataset."""

    total_records: int = Field(default=0, ge=0)
    statistics: List[ColumnStatistics] = Field(default_factory=list)
    correlations: Optional[CorrelationMatrix] = None
    summary: str = Field(default="", description="Explanatory text summary for Core reasoning")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="before")
    @classmethod
    def normalize_statistics(cls, data: Any) -> Any:
        if isinstance(data, dict):
            stats = data.get("statistics")
            if isinstance(stats, dict):
                data["statistics"] = list(stats.values())
        return data

    @property
    def summary_markdown(self) -> str:
        return self.summary

    @property
    def correlation_matrix(self) -> Optional[CorrelationMatrix]:
        return self.correlations


# -----------------------------------------------------------------------------
# Visualization Schemas
# -----------------------------------------------------------------------------
class ChartType(str, Enum):
    """Standard chart and visualization types."""

    BAR = "bar"
    LINE = "line"
    HISTOGRAM = "histogram"
    SCATTER = "scatter"
    PIE = "pie"


class ChartSpec(BaseModel):
    """Structured specification of a data chart."""

    chart_type: ChartType = Field(default=ChartType.BAR, description="Type of visual chart")
    title: str = Field(default="Data Chart", description="Chart title")
    x_column: Optional[str] = Field(default=None, description="Column mapped to X-axis")
    y_column: Optional[str] = Field(default=None, description="Column mapped to Y-axis")
    x_axis: Optional[str] = Field(default=None, description="Alias for x_column")
    y_axis: Optional[str] = Field(default=None, description="Alias for y_column")
    bins: int = Field(default=10, ge=1, le=50, description="Bin count for histograms")
    labels: List[str] = Field(default_factory=list, description="Categorical or bin labels")
    series: Dict[str, List[float]] = Field(default_factory=dict, description="Named numeric series")

    @model_validator(mode="after")
    def sync_axis_aliases(self) -> "ChartSpec":
        if self.x_axis and not self.x_column:
            self.x_column = self.x_axis
        elif self.x_column and not self.x_axis:
            self.x_axis = self.x_column

        if self.y_axis and not self.y_column:
            self.y_column = self.y_axis
        elif self.y_column and not self.y_axis:
            self.y_axis = self.y_column
        return self


class VisualizationResult(BaseModel):
    """Structured and textual representations of a rendered visualization."""

    chart_spec: Optional[ChartSpec] = None
    spec: Optional[ChartSpec] = None
    ascii_representation: Optional[str] = None
    ascii_chart: Optional[str] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    summary: str = Field(default="")
    format: str = Field(default="json_chart_spec")

    @model_validator(mode="after")
    def sync_vis_fields(self) -> "VisualizationResult":
        if self.spec and not self.chart_spec:
            self.chart_spec = self.spec
        elif self.chart_spec and not self.spec:
            self.spec = self.chart_spec

        if self.ascii_chart and not self.ascii_representation:
            self.ascii_representation = self.ascii_chart
        elif self.ascii_representation and not self.ascii_chart:
            self.ascii_chart = self.ascii_representation
        return self


# -----------------------------------------------------------------------------
# Verification Schemas
# -----------------------------------------------------------------------------
class DataValidationRule(BaseModel):
    """A single constraint or validation rule applied to a dataset."""

    rule_name: str = Field(..., description="Unique rule name or check type")
    check_type: Optional[str] = Field(
        default=None,
        description="Rule type: 'not_null', 'unique', 'value_range', 'allowed_values', 'regex', 'column_exists', 'row_count'",
    )
    column: Optional[str] = Field(default=None, description="Target column")
    params: Dict[str, Any] = Field(default_factory=dict, description="Rule parameters (min, max, pattern, etc.)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Alias for params")

    @model_validator(mode="after")
    def sync_rule_fields(self) -> "DataValidationRule":
        if not self.check_type:
            self.check_type = self.rule_name
        if self.parameters and not self.params:
            self.params = self.parameters
        elif self.params and not self.parameters:
            self.parameters = self.params
        return self


class VerificationFinding(BaseModel):
    """Outcome of a single validation rule verification."""

    rule_name: str = Field(...)
    passed: bool = Field(default=True)
    severity: str = Field(default="error")
    message: str = Field(...)
    column: Optional[str] = None
    invalid_count: int = Field(default=0, ge=0)
    failed_row_indices: List[int] = Field(default_factory=list)


class DataVerificationReport(BaseModel):
    """Aggregated verification results for dataset integrity."""

    is_valid: bool = Field(default=True)
    rules_checked: int = Field(default=0, ge=0)
    rules_passed: int = Field(default=0, ge=0)
    rules_failed: int = Field(default=0, ge=0)
    total_rules: Optional[int] = None
    passed_rules: Optional[int] = None
    failed_rules: Optional[int] = None
    quality_score: Optional[float] = None
    findings: List[VerificationFinding] = Field(default_factory=list)
    summary: str = Field(default="")

    @model_validator(mode="after")
    def sync_report_counts(self) -> "DataVerificationReport":
        if self.total_rules is None:
            self.total_rules = self.rules_checked
        else:
            self.rules_checked = self.total_rules

        if self.passed_rules is None:
            self.passed_rules = self.rules_passed
        else:
            self.rules_passed = self.passed_rules

        if self.failed_rules is None:
            self.failed_rules = self.rules_failed
        else:
            self.rules_failed = self.failed_rules

        if self.quality_score is None:
            self.quality_score = round(self.rules_passed / self.rules_checked, 2) if self.rules_checked > 0 else 1.0
        return self


# -----------------------------------------------------------------------------
# Dataset Schema
# -----------------------------------------------------------------------------
class StructuredDataset(BaseModel):
    """In-memory tabular dataset with column schema and records."""

    name: str = Field(default="dataset")
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    format: DataFormat = Field(default=DataFormat.DICT)

    @property
    def row_count(self) -> CountInt:
        """Total number of records in dataset (callable or integer)."""
        return CountInt(len(self.rows))

    @property
    def column_count(self) -> CountInt:
        """Total number of columns in dataset (callable or integer)."""
        return CountInt(len(self.columns))

    @property
    def data(self) -> List[Dict[str, Any]]:
        """Direct access to rows list."""
        return self.rows

    def column_names(self) -> List[str]:
        """Return list of column names."""
        return list(self.columns)

    def get_column_values(self, column: str) -> List[Any]:
        """Extract all values for a given column name."""
        return [r.get(column) for r in self.rows]

    def to_dict(self) -> List[Dict[str, Any]]:
        """Return dataset rows as a list of dicts."""
        return [dict(r) for r in self.rows]

    def to_csv(self, delimiter: str = ",") -> str:
        """Serialize dataset into CSV text."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.columns, delimiter=delimiter, lineterminator="\n")
        writer.writeheader()
        for r in self.rows:
            writer.writerow({col: r.get(col, "") for col in self.columns})
        return output.getvalue()

    def to_json(self) -> str:
        """Serialize dataset into JSON text."""
        return json.dumps(self.rows, indent=2, default=str)

    @classmethod
    def from_records(cls, records: Sequence[Dict[str, Any]], name: str = "dataset") -> "StructuredDataset":
        """Create StructuredDataset from a sequence of record dictionaries."""
        records_list = [dict(r) for r in records]
        columns: List[str] = []
        for r in records_list:
            for k in r.keys():
                if k not in columns:
                    columns.append(k)
        return cls(name=name, columns=columns, rows=records_list, format=DataFormat.DICT)

    @classmethod
    def from_columns(cls, columns_dict: Dict[str, Sequence[Any]], name: str = "dataset") -> "StructuredDataset":
        """Create StructuredDataset from a columnar dictionary of lists."""
        cols = list(columns_dict.keys())
        if not cols:
            return cls(name=name, columns=[], rows=[], format=DataFormat.DICT)
        num_rows = len(columns_dict[cols[0]])
        rows: List[Dict[str, Any]] = []
        for i in range(num_rows):
            row = {c: columns_dict[c][i] if i < len(columns_dict[c]) else None for c in cols}
            rows.append(row)
        return cls(name=name, columns=cols, rows=rows, format=DataFormat.DICT)


# -----------------------------------------------------------------------------
# Input and Result Payloads
# -----------------------------------------------------------------------------
class DataInput(BaseModel):
    """Input payload for Data Plugin operations."""

    operation: DataOperation = Field(
        default=DataOperation.INSPECT,
        description="Data operation to execute",
    )
    data: Optional[Union[str, List[Dict[str, Any]], Dict[str, Any]]] = Field(
        default=None,
        description="Raw dataset payload (CSV string, JSON string, list of dicts, or columnar dict)",
    )
    records: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Alias for in-memory records list",
    )
    dataset_name: Optional[str] = Field(
        default=None,
        description="Optional name for ingested dataset",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Filesystem path to dataset file (CSV or JSON)",
    )
    dataset: Optional[StructuredDataset] = Field(
        default=None,
        description="Pre-ingested StructuredDataset",
    )
    format: Optional[Union[DataFormat, str]] = Field(
        default=None,
        description="Input data format if known",
    )
    cleaning_rules: Optional[Union[CleaningRule, List[CleaningRule], Sequence[CleaningRule]]] = Field(
        default=None,
        description="Rules for cleaning operation",
    )
    transform_config: Optional[TransformConfig] = Field(
        default=None,
        description="Configuration for transformation operation",
    )
    analysis_columns: Optional[List[str]] = Field(
        default=None,
        description="Columns to restrict statistical analysis to",
    )
    include_correlations: bool = Field(
        default=False,
        description="Whether to compute pairwise correlations during analysis",
    )
    visualization_spec: Optional[ChartSpec] = Field(
        default=None,
        description="Detailed chart specification",
    )
    chart_spec: Optional[ChartSpec] = Field(
        default=None,
        description="Alias for visualization_spec",
    )
    chart_type: Optional[Union[ChartType, str]] = Field(
        default=None,
        description="Quick chart type for visualization",
    )
    chart_x: Optional[str] = Field(
        default=None,
        description="X-axis column for quick chart",
    )
    chart_y: Optional[str] = Field(
        default=None,
        description="Y-axis column for quick chart",
    )
    verification_rules: Optional[List[DataValidationRule]] = Field(
        default=None,
        description="Data constraints for verification operation",
    )
    validation_rules: Optional[List[DataValidationRule]] = Field(
        default=None,
        description="Alias for verification_rules",
    )
    options: Dict[str, Any] = Field(default_factory=dict, description="Adapter / ingestion options")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary caller metadata")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def validate_inputs(self) -> "DataInput":
        """Normalize inputs and verify that some form of data source is provided."""
        if self.records is not None and self.data is None:
            self.data = self.records
        if self.validation_rules is not None and self.verification_rules is None:
            self.verification_rules = self.validation_rules
        elif self.verification_rules is not None and self.validation_rules is None:
            self.validation_rules = self.verification_rules
        if self.chart_spec is not None and self.visualization_spec is None:
            self.visualization_spec = self.chart_spec
        elif self.visualization_spec is not None and self.chart_spec is None:
            self.chart_spec = self.visualization_spec

        if self.options and not self.metadata:
            self.metadata = dict(self.options)
        elif self.metadata and not self.options:
            self.options = dict(self.metadata)

        if self.dataset_name:
            self.metadata.setdefault("name", self.dataset_name)

        if self.data is None and self.file_path is None and self.dataset is None and self.records is None:
            raise ValueError("Data operation requires one of 'data', 'file_path', 'dataset', or 'records'.")
        return self


class DataResult(BaseModel):
    """Standard structured result returned by the Data Plugin."""

    operation: DataOperation = Field(..., description="Executed data operation")
    success: bool = Field(default=True, description="Whether operation succeeded")
    dataset: Optional[StructuredDataset] = Field(default=None, description="Resulting dataset if transformed or ingested")
    inspection: Optional[InspectionReport] = Field(default=None, description="Dataset inspection profile")
    inspection_report: Optional[InspectionReport] = Field(default=None, description="Alias for inspection")
    cleaning: Optional[CleaningReport] = Field(default=None, description="Cleaning transformation report")
    cleaning_report: Optional[CleaningReport] = Field(default=None, description="Alias for cleaning")
    transformation: Optional[TransformReport] = Field(default=None, description="Transformation report")
    transform_report: Optional[TransformReport] = Field(default=None, description="Alias for transformation")
    analysis: Optional[AnalysisReport] = Field(default=None, description="Statistical analysis and correlations")
    analysis_report: Optional[AnalysisReport] = Field(default=None, description="Alias for analysis")
    visualization: Optional[VisualizationResult] = Field(default=None, description="Visualization result")
    visualization_result: Optional[VisualizationResult] = Field(default=None, description="Alias for visualization")
    verification: Optional[DataVerificationReport] = Field(default=None, description="Data verification report")
    verification_report: Optional[DataVerificationReport] = Field(default=None, description="Alias for verification")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Execution timing and row statistics")
    error: Optional[str] = Field(default=None, description="Error message if operation failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

    @model_validator(mode="after")
    def sync_result_fields(self) -> "DataResult":
        if self.inspection and not self.inspection_report:
            self.inspection_report = self.inspection
        elif self.inspection_report and not self.inspection:
            self.inspection = self.inspection_report

        if self.cleaning and not self.cleaning_report:
            self.cleaning_report = self.cleaning
        elif self.cleaning_report and not self.cleaning:
            self.cleaning = self.cleaning_report

        if self.transformation and not self.transform_report:
            self.transform_report = self.transformation
        elif self.transform_report and not self.transformation:
            self.transformation = self.transform_report

        if self.analysis and not self.analysis_report:
            self.analysis_report = self.analysis
        elif self.analysis_report and not self.analysis:
            self.analysis = self.analysis_report

        if self.visualization and not self.visualization_result:
            self.visualization_result = self.visualization
        elif self.visualization_result and not self.visualization:
            self.visualization = self.visualization_result

        if self.verification and not self.verification_report:
            self.verification_report = self.verification
        elif self.verification_report and not self.verification:
            self.verification = self.verification_report
        return self


__all__ = [
    "CountInt",
    "DataOperation",
    "DataFormat",
    "ColumnType",
    "ColumnInfo",
    "InspectionReport",
    "CleaningRule",
    "CleaningReport",
    "TransformConfig",
    "TransformReport",
    "ColumnStatistics",
    "CorrelationMatrix",
    "AnalysisReport",
    "ChartType",
    "ChartSpec",
    "VisualizationResult",
    "DataValidationRule",
    "VerificationFinding",
    "DataVerificationReport",
    "StructuredDataset",
    "DataInput",
    "DataResult",
]
