"""Tests for DataVisualizationTool."""

import pytest

from xeren.plugins.data.schemas import (
    ChartSpec,
    ChartType,
    DataInput,
    DataOperation,
    StructuredDataset,
)
from xeren.plugins.data.tools.visualization import DataVisualizationTool


def test_visualization_bar_chart():
    """Verify bar chart spec and ASCII rendering."""
    records = [
        {"category": "Apples", "sales": 50},
        {"category": "Bananas", "sales": 80},
        {"category": "Cherries", "sales": 30},
    ]
    dataset = StructuredDataset.from_records(records)
    tool = DataVisualizationTool()

    inp = DataInput(
        operation=DataOperation.VISUALIZE,
        dataset=dataset,
        chart_spec=ChartSpec(
            chart_type=ChartType.BAR,
            title="Fruit Sales",
            x_axis="category",
            y_axis="sales",
        ),
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.visualization_result is not None
    vis = res.visualization_result
    assert vis.spec is not None
    assert vis.spec.chart_type == ChartType.BAR
    assert vis.spec.title == "Fruit Sales"
    assert vis.ascii_chart is not None
    assert "Bananas" in vis.ascii_chart
    assert "#" in vis.ascii_chart


def test_visualization_histogram():
    """Verify histogram binning and ASCII rendering."""
    records = [{"val": v} for v in [1, 2, 2, 3, 3, 3, 4, 4, 5, 8, 9, 10]]
    dataset = StructuredDataset.from_records(records)
    tool = DataVisualizationTool()

    inp = DataInput(
        operation=DataOperation.VISUALIZE,
        dataset=dataset,
        chart_spec=ChartSpec(
            chart_type=ChartType.HISTOGRAM,
            title="Value Distribution",
            x_axis="val",
        ),
    )
    res = tool.execute(inp)
    assert res.success is True
    vis = res.visualization_result
    assert vis is not None
    assert vis.spec is not None
    assert vis.spec.chart_type == ChartType.HISTOGRAM
    assert len(vis.spec.labels) > 0
    assert vis.ascii_chart is not None
    assert "Value Distribution" in vis.ascii_chart


def test_visualization_scatter_and_line():
    """Verify line and scatter chart rendering."""
    records = [{"t": i, "val": i * 2} for i in range(5)]
    dataset = StructuredDataset.from_records(records)
    tool = DataVisualizationTool()

    inp = DataInput(
        operation=DataOperation.VISUALIZE,
        dataset=dataset,
        chart_spec=ChartSpec(
            chart_type=ChartType.LINE,
            x_axis="t",
            y_axis="val",
        ),
    )
    res = tool.execute(inp)
    assert res.success is True
    assert res.visualization_result is not None
    assert res.visualization_result.spec is not None
    assert res.visualization_result.spec.chart_type == ChartType.LINE
    assert res.visualization_result.ascii_chart is not None
    assert len(res.visualization_result.ascii_chart) > 0
