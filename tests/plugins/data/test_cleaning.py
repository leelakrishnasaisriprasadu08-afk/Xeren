"""Tests for DataCleaningTool."""

import pytest

from xeren.plugins.data.schemas import (
    CleaningRule,
    DataInput,
    DataOperation,
    StructuredDataset,
)
from xeren.plugins.data.tools.cleaning import DataCleaningTool


def test_cleaning_tool_deduplicate_and_trim():
    """Verify deduplication and string whitespace trimming."""
    records = [
        {"id": 1, "name": " Alice  ", "role": "Engineer"},
        {"id": 1, "name": " Alice  ", "role": "Engineer"},
        {"id": 2, "name": "  Bob ", "role": "Manager"},
    ]
    dataset = StructuredDataset.from_records(records)
    tool = DataCleaningTool()

    inp = DataInput(
        operation=DataOperation.CLEAN,
        dataset=dataset,
        cleaning_rules=[
            CleaningRule(rule_type="drop_duplicates"),
            CleaningRule(rule_type="trim_strings"),
        ],
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.row_count() == 2
    assert res.dataset.data[0]["name"] == "Alice"
    assert res.dataset.data[1]["name"] == "Bob"
    assert res.cleaning_report is not None
    assert res.cleaning_report.rows_removed == 1


def test_cleaning_tool_impute_missing_mean_and_constant():
    """Verify imputation of numeric columns via mean and string columns via constant."""
    records = [
        {"val": 10.0, "status": "active"},
        {"val": 20.0, "status": None},
        {"val": None, "status": "inactive"},
    ]
    dataset = StructuredDataset.from_records(records)
    tool = DataCleaningTool()

    inp = DataInput(
        operation=DataOperation.CLEAN,
        dataset=dataset,
        cleaning_rules=[
            CleaningRule(rule_type="impute_missing", column="val", parameters={"strategy": "mean"}),
            CleaningRule(rule_type="impute_missing", column="status", parameters={"strategy": "constant", "value": "unknown"}),
        ],
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    # Mean of 10 and 20 is 15.0
    assert res.dataset.data[2]["val"] == 15.0
    assert res.dataset.data[1]["status"] == "unknown"


def test_cleaning_tool_rename_columns():
    """Verify column renaming."""
    records = [{"old_a": 1, "old_b": 2}]
    dataset = StructuredDataset.from_records(records)
    tool = DataCleaningTool()

    inp = DataInput(
        operation=DataOperation.CLEAN,
        dataset=dataset,
        cleaning_rules=[
            CleaningRule(
                rule_type="rename_columns",
                parameters={"mapping": {"old_a": "new_a", "old_b": "new_b"}},
            )
        ],
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.column_names() == ["new_a", "new_b"]
    assert res.dataset.data[0]["new_a"] == 1


def test_cleaning_tool_type_casting():
    """Verify type casting cleaning rule."""
    records = [{"age": "30", "score": "95.5"}]
    dataset = StructuredDataset.from_records(records)
    tool = DataCleaningTool()

    inp = DataInput(
        operation=DataOperation.CLEAN,
        dataset=dataset,
        cleaning_rules=[
            CleaningRule(rule_type="cast_types", parameters={"casts": {"age": "int", "score": "float"}})
        ],
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.data[0]["age"] == 30
    assert res.dataset.data[0]["score"] == 95.5
