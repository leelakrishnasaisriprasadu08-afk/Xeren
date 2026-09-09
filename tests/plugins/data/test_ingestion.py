"""Tests for DataIngestionTool and format adapters."""

import os
import tempfile
import pytest

from xeren.plugins.data.schemas import (
    ColumnType,
    DataFormat,
    DataInput,
    DataOperation,
)
from xeren.plugins.data.tools.ingestion import (
    CSVDataAdapter,
    DataIngestionTool,
    DictDataAdapter,
    JSONDataAdapter,
)


def test_csv_adapter_parsing():
    """Verify CSV adapter parses standard CSV with headers and infers types."""
    csv_content = """name,age,salary,active
Alice,30,75000.50,true
Bob,25,50000.00,false
Charlie,35,,true
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        path = f.name

    try:
        adapter = CSVDataAdapter()
        ds = adapter.load(path)
        assert ds.row_count() == 3
        assert ds.column_names() == ["name", "age", "salary", "active"]
        assert ds.data[0]["name"] == "Alice"
        assert ds.data[0]["age"] == 30
        assert ds.data[0]["salary"] == 75000.50
        assert ds.data[0]["active"] is True
        assert ds.data[2]["salary"] is None
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_csv_adapter_semicolon_delimiter():
    """Verify CSV adapter handles semicolon delimiter automatically or via options."""
    csv_content = "id;item;price\n1;Apple;1.5\n2;Banana;0.75\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        path = f.name

    try:
        adapter = CSVDataAdapter()
        ds = adapter.load(path)
        assert ds.row_count() == 2
        assert ds.column_names() == ["id", "item", "price"]
        assert ds.data[0]["item"] == "Apple"
        assert ds.data[0]["price"] == 1.5
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_json_adapter_records_format():
    """Verify JSON adapter parses records array format."""
    json_content = '[{"city": "Paris", "temp": 18.5}, {"city": "Berlin", "temp": 16.0}]'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json_content)
        path = f.name

    try:
        adapter = JSONDataAdapter()
        ds = adapter.load(path)
        assert ds.row_count() == 2
        assert ds.column_names() == ["city", "temp"]
        assert ds.data[0]["city"] == "Paris"
        assert ds.data[0]["temp"] == 18.5
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_json_adapter_columnar_format():
    """Verify JSON adapter parses columnar dict format."""
    json_content = '{"city": ["Tokyo", "Seoul"], "temp": [22.0, 20.5]}'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json_content)
        path = f.name

    try:
        adapter = JSONDataAdapter()
        ds = adapter.load(path)
        assert ds.row_count() == 2
        assert ds.column_names() == ["city", "temp"]
        assert ds.data[0]["city"] == "Tokyo"
        assert ds.data[1]["city"] == "Seoul"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_dict_adapter():
    """Verify DictDataAdapter creates dataset from in-memory records."""
    records = [{"a": 100, "b": "test"}, {"a": 200, "b": "demo"}]
    adapter = DictDataAdapter()
    ds = adapter.load(records, dataset_name="in_memory")
    assert ds.name == "in_memory"
    assert ds.row_count() == 2
    assert ds.data[1]["a"] == 200


def test_ingestion_tool_safe_path_validation():
    """Verify DataIngestionTool blocks directory traversal attempts."""
    tool = DataIngestionTool()
    inp = DataInput(
        operation=DataOperation.INGEST,
        file_path="../../etc/passwd",
    )
    res = tool.execute(inp)
    assert res.success is False
    assert res.error is not None
    assert "Invalid file path" in res.error or "Path traversal" in res.error


def test_ingestion_tool_file_not_found():
    """Verify DataIngestionTool handles non-existent files cleanly."""
    tool = DataIngestionTool()
    inp = DataInput(
        operation=DataOperation.INGEST,
        file_path="non_existent_file_123456789.csv",
    )
    res = tool.execute(inp)
    assert res.success is False
    assert res.error is not None
    assert "not found" in res.error.lower()


def test_ingestion_tool_raw_records():
    """Verify DataIngestionTool ingests directly from records in DataInput."""
    tool = DataIngestionTool()
    inp = DataInput(
        operation=DataOperation.INGEST,
        records=[{"x": 1, "y": 2}, {"x": 3, "y": 4}],
        dataset_name="quick_data",
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.name == "quick_data"
    assert res.dataset.row_count() == 2
