"""Tests for DataWorkflow execution across all operations."""

import pytest

from xeren.plugins.data.registry import DataToolRegistry
from xeren.plugins.data.schemas import (
    CleaningRule,
    DataInput,
    DataOperation,
    DataResult,
    StructuredDataset,
    TransformConfig,
)
from xeren.plugins.data.workflow import DataWorkflow


@pytest.fixture
def workflow():
    registry = DataToolRegistry()
    return DataWorkflow(registry=registry)


@pytest.fixture
def sample_dataset():
    return StructuredDataset.from_records(
        [
            {"item": "Widget A", "price": 25.0, "qty": 10},
            {"item": "Widget B", "price": 40.0, "qty": 5},
            {"item": "Widget A", "price": 25.0, "qty": 10},  # duplicate
        ]
    )


def test_workflow_inspect_operation(workflow, sample_dataset):
    """Verify workflow executes inspect operation."""
    inp = DataInput(operation=DataOperation.INSPECT, dataset=sample_dataset)
    res = workflow.run(inp)
    assert res.success is True
    assert res.operation == DataOperation.INSPECT
    assert res.inspection_report is not None
    assert res.inspection_report.row_count == 3


def test_workflow_clean_operation(workflow, sample_dataset):
    """Verify workflow executes clean operation."""
    inp = DataInput(
        operation=DataOperation.CLEAN,
        dataset=sample_dataset,
        cleaning_rules=[CleaningRule(rule_type="drop_duplicates")],
    )
    res = workflow.run(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.row_count() == 2
    assert res.cleaning_report is not None
    assert res.cleaning_report.rows_removed == 1


def test_workflow_transform_operation(workflow, sample_dataset):
    """Verify workflow executes transform operation."""
    inp = DataInput(
        operation=DataOperation.TRANSFORM,
        dataset=sample_dataset,
        transform_config=TransformConfig(
            filters=[{"column": "price", "operator": ">", "value": 30.0}]
        ),
    )
    res = workflow.run(inp)
    assert res.success is True
    assert res.dataset is not None
    assert res.dataset.row_count() == 1
    assert res.dataset.data[0]["item"] == "Widget B"


def test_workflow_analyze_operation(workflow, sample_dataset):
    """Verify workflow executes analyze operation."""
    inp = DataInput(operation=DataOperation.ANALYZE, dataset=sample_dataset)
    res = workflow.run(inp)
    assert res.success is True
    assert res.analysis_report is not None
    assert res.analysis_report.total_records == 3


def test_workflow_visualize_operation(workflow, sample_dataset):
    """Verify workflow executes visualize operation."""
    inp = DataInput(operation=DataOperation.VISUALIZE, dataset=sample_dataset)
    res = workflow.run(inp)
    assert res.success is True
    assert res.visualization_result is not None


@pytest.mark.asyncio
async def test_workflow_async_run(workflow, sample_dataset):
    """Verify workflow asynchronous execution (arun)."""
    inp = DataInput(operation=DataOperation.INSPECT, dataset=sample_dataset)
    res = await workflow.arun(inp)
    assert res.success is True
    assert res.operation == DataOperation.INSPECT
    assert res.inspection_report is not None
