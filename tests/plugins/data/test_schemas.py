"""Tests for DataPlugin schemas and StructuredDataset operations."""

import pytest

from xeren.plugins.data.schemas import (
    AnalysisReport,
    ChartSpec,
    ChartType,
    CleaningReport,
    CleaningRule,
    ColumnInfo,
    ColumnStatistics,
    ColumnType,
    DataFormat,
    DataInput,
    DataOperation,
    DataResult,
    DataValidationRule,
    DataVerificationReport,
    InspectionReport,
    StructuredDataset,
    TransformConfig,
    TransformReport,
    VerificationFinding,
    VisualizationResult,
)


def test_structured_dataset_from_records():
    """Verify StructuredDataset creation from row records."""
    records = [
        {"id": 1, "name": "Alice", "score": 95.5},
        {"id": 2, "name": "Bob", "score": 88.0},
        {"id": 3, "name": "Charlie", "score": None},
    ]
    ds = StructuredDataset.from_records(records, name="students")
    assert ds.name == "students"
    assert ds.row_count() == 3
    assert ds.column_count() == 3
    assert ds.column_names() == ["id", "name", "score"]
    assert ds.get_column_values("name") == ["Alice", "Bob", "Charlie"]
    assert ds.get_column_values("score") == [95.5, 88.0, None]


def test_structured_dataset_from_columns():
    """Verify StructuredDataset creation from columnar dictionary."""
    columns = {
        "x": [10, 20, 30],
        "y": ["a", "b", "c"],
    }
    ds = StructuredDataset.from_columns(columns, name="coords")
    assert ds.row_count() == 3
    assert ds.column_names() == ["x", "y"]
    assert ds.data[0] == {"x": 10, "y": "a"}
    assert ds.data[2] == {"x": 30, "y": "c"}


def test_structured_dataset_to_csv():
    """Verify StructuredDataset export to CSV string."""
    records = [
        {"id": 1, "val": "hello"},
        {"id": 2, "val": "world"},
    ]
    ds = StructuredDataset.from_records(records)
    csv_out = ds.to_csv()
    assert "id,val" in csv_out
    assert "1,hello" in csv_out
    assert "2,world" in csv_out


def test_structured_dataset_to_json():
    """Verify StructuredDataset export to JSON string."""
    records = [{"x": 1, "y": 2}]
    ds = StructuredDataset.from_records(records)
    json_out = ds.to_json()
    assert '"x": 1' in json_out
    assert '"y": 2' in json_out


def test_data_input_validation():
    """Verify DataInput validation and defaults."""
    inp = DataInput(
        operation=DataOperation.INSPECT,
        records=[{"a": 1, "b": 2}],
    )
    assert inp.operation == DataOperation.INSPECT
    assert inp.records is not None
    assert len(inp.records) == 1
    assert inp.options == {}


def test_data_result_serialization():
    """Verify DataResult serialization and deserialization roundtrip."""
    res = DataResult(
        operation=DataOperation.CLEAN,
        success=True,
        dataset=StructuredDataset.from_records([{"a": 1}]),
        cleaning_report=CleaningReport(
            initial_rows=2,
            final_rows=1,
            rows_removed=1,
            columns_modified=["a"],
            actions_taken=["deduplication"],
        ),
    )
    dumped = res.model_dump()
    assert dumped["operation"] == "clean"
    assert dumped["success"] is True
    assert dumped["cleaning_report"]["rows_removed"] == 1

    restored = DataResult.model_validate(dumped)
    assert restored.operation == DataOperation.CLEAN
    assert restored.cleaning_report is not None
    assert restored.cleaning_report.rows_removed == 1


def test_chart_spec_and_visualization_result():
    """Verify ChartSpec and VisualizationResult creation."""
    spec = ChartSpec(
        chart_type=ChartType.BAR,
        title="Category Counts",
        x_axis="category",
        y_axis="count",
        labels=["A", "B", "C"],
        series={"count": [10.0, 25.0, 15.0]},
    )
    vis = VisualizationResult(
        spec=spec,
        ascii_chart="A: ####\nB: ##########\nC: ######",
        summary="Bar chart of categories",
    )
    assert vis.spec is not None
    assert vis.spec.chart_type == ChartType.BAR
    assert vis.ascii_chart is not None
    assert "A: ####" in vis.ascii_chart


def test_verification_report_schema():
    """Verify DataVerificationReport and VerificationFinding models."""
    finding = VerificationFinding(
        rule_name="not_null",
        column="email",
        passed=False,
        severity="error",
        message="Found 3 null values in column 'email'",
        failed_row_indices=[2, 5, 8],
    )
    report = DataVerificationReport(
        total_rules=5,
        passed_rules=4,
        failed_rules=1,
        findings=[finding],
        is_valid=False,
        quality_score=0.8,
    )
    assert report.total_rules == 5
    assert report.quality_score == 0.8
    assert len(report.findings) == 1
    assert report.findings[0].failed_row_indices == [2, 5, 8]
