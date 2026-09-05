"""Tests for DataInspectionTool and dataset profiling."""

import pytest

from xeren.plugins.data.schemas import (
    ColumnType,
    DataInput,
    DataOperation,
    StructuredDataset,
)
from xeren.plugins.data.tools.inspection import DataInspectionTool


def test_inspection_tool_profiles_types_and_nulls():
    """Verify inspection tool accurately profiles column types, null counts, and samples."""
    dataset = StructuredDataset.from_records(
        [
            {"id": 1, "name": "Alice", "score": 90.0, "active": True, "created": "2025-01-01T10:00:00"},
            {"id": 2, "name": "Bob", "score": None, "active": False, "created": "2025-01-02T10:00:00"},
            {"id": 3, "name": "Charlie", "score": 85.5, "active": True, "created": None},
        ],
        name="test_profile",
    )

    tool = DataInspectionTool()
    inp = DataInput(
        operation=DataOperation.INSPECT,
        dataset=dataset,
    )
    result = tool.execute(inp)
    assert result.success is True
    report = result.inspection_report
    assert report is not None
    assert report.row_count == 3
    assert report.column_count == 5

    # Check columns
    col_map = {col.name: col for col in report.columns}
    assert col_map["id"].inferred_type == ColumnType.INTEGER
    assert col_map["id"].null_count == 0

    assert col_map["name"].inferred_type == ColumnType.STRING
    assert col_map["name"].distinct_count == 3

    assert col_map["score"].inferred_type == ColumnType.FLOAT
    assert col_map["score"].null_count == 1
    assert col_map["score"].null_percentage == pytest.approx(33.33, rel=1e-2)

    assert col_map["active"].inferred_type == ColumnType.BOOLEAN
    assert col_map["created"].inferred_type == ColumnType.DATETIME


def test_inspection_tool_duplicate_rows():
    """Verify inspection tool detects duplicate rows."""
    dataset = StructuredDataset.from_records(
        [
            {"a": 1, "b": "dup"},
            {"a": 1, "b": "dup"},
            {"a": 2, "b": "unique"},
        ]
    )
    tool = DataInspectionTool()
    inp = DataInput(operation=DataOperation.INSPECT, dataset=dataset)
    res = tool.execute(inp)
    assert res.success is True
    assert res.inspection_report is not None
    assert res.inspection_report.duplicate_rows == 1


def test_inspection_tool_empty_dataset():
    """Verify inspection tool handles empty dataset gracefully."""
    dataset = StructuredDataset.from_records([])
    tool = DataInspectionTool()
    inp = DataInput(operation=DataOperation.INSPECT, dataset=dataset)
    res = tool.execute(inp)
    assert res.success is True
    assert res.inspection_report is not None
    assert res.inspection_report.row_count == 0
    assert res.inspection_report.column_count == 0
