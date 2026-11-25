"""Tests for DataTransformationTool."""

import pytest

from xeren.plugins.data.schemas import (
    DataInput,
    DataOperation,
    StructuredDataset,
    TransformConfig,
)
from xeren.plugins.data.tools.transformation import DataTransformationTool


@pytest.fixture
def sample_employees():
    return StructuredDataset.from_records(
        [
            {"id": 1, "dept": "Eng", "salary": 100000, "age": 30},
            {"id": 2, "dept": "Eng", "salary": 120000, "age": 35},
            {"id": 3, "dept": "Sales", "salary": 80000, "age": 28},
            {"id": 4, "dept": "Sales", "salary": 90000, "age": 40},
            {"id": 5, "dept": "HR", "salary": 70000, "age": 25},
        ]
    )


def test_transform_filter_and_sort(sample_employees):
    """Verify filtering and sorting rows."""
    tool = DataTransformationTool()
    cfg = TransformConfig(
        filters=[{"column": "salary", "operator": ">=", "value": 90000}],
        sort_by=[{"column": "salary", "ascending": False}],
    )
    inp = DataInput(
        operation=DataOperation.TRANSFORM,
        dataset=sample_employees,
        transform_config=cfg,
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.row_count() == 3
    # Sorted desc by salary: 120000, 100000, 90000
    assert res.dataset.data[0]["id"] == 2
    assert res.dataset.data[1]["id"] == 1
    assert res.dataset.data[2]["id"] == 4


def test_transform_group_by_and_aggregation(sample_employees):
    """Verify group_by with aggregation functions (avg, count, sum, max, min)."""
    tool = DataTransformationTool()
    cfg = TransformConfig(
        group_by=["dept"],
        aggregations={
            "salary": "avg",
            "age": "max",
            "id": "count",
        },
        sort_by=[{"column": "dept", "ascending": True}],
    )
    inp = DataInput(
        operation=DataOperation.TRANSFORM,
        dataset=sample_employees,
        transform_config=cfg,
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.row_count() == 3
    dept_map = {r["dept"]: r for r in res.dataset.data}

    # Eng has 100000 and 120000 -> avg = 110000.0, count = 2, max age = 35
    assert dept_map["Eng"]["salary_avg"] == 110000.0
    assert dept_map["Eng"]["age_max"] == 35
    assert dept_map["Eng"]["id_count"] == 2

    # HR has 1 employee
    assert dept_map["HR"]["salary_avg"] == 70000.0
    assert dept_map["HR"]["id_count"] == 1


def test_transform_projection_and_pagination(sample_employees):
    """Verify column selection, limit, and offset."""
    tool = DataTransformationTool()
    cfg = TransformConfig(
        select_columns=["id", "dept"],
        sort_by=[{"column": "id", "ascending": True}],
        limit=2,
        offset=1,
    )
    inp = DataInput(
        operation=DataOperation.TRANSFORM,
        dataset=sample_employees,
        transform_config=cfg,
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.row_count() == 2
    assert res.dataset.column_names() == ["id", "dept"]
    # Offset 1 should skip id 1, returning ids 2 and 3
    assert res.dataset.data[0]["id"] == 2
    assert res.dataset.data[1]["id"] == 3
