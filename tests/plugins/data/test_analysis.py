"""Tests for DataAnalysisTool and statistical computations."""

import pytest

from xeren.plugins.data.schemas import (
    DataInput,
    DataOperation,
    StructuredDataset,
)
from xeren.plugins.data.tools.analysis import DataAnalysisTool


def test_analysis_tool_statistics_and_correlations():
    """Verify statistical profiling and correlation matrix calculations."""
    records = [
        {"height": 160, "weight": 55, "gender": "F"},
        {"height": 170, "weight": 65, "gender": "F"},
        {"height": 180, "weight": 75, "gender": "M"},
        {"height": 190, "weight": 85, "gender": "M"},
    ]
    dataset = StructuredDataset.from_records(records, name="biometrics")
    tool = DataAnalysisTool()

    inp = DataInput(
        operation=DataOperation.ANALYZE,
        dataset=dataset,
    )
    res = tool.execute(inp)
    assert res.success is True
    report = res.analysis_report
    assert report is not None
    assert report.total_records == 4

    # Height stats
    height_stats = next(s for s in report.statistics if s.column_name == "height")
    assert height_stats.mean == 175.0
    assert height_stats.min_value == 160.0
    assert height_stats.max_value == 190.0
    assert height_stats.median == 175.0

    # Categorical top values
    gender_stats = next(s for s in report.statistics if s.column_name == "gender")
    assert gender_stats.top_values == {"F": 2, "M": 2}

    # Correlation between height and weight (perfect linear relationship = 1.0)
    matrix = report.correlation_matrix
    assert matrix is not None
    assert "height" in matrix.columns
    assert "weight" in matrix.columns
    height_idx = matrix.columns.index("height")
    weight_idx = matrix.columns.index("weight")
    corr = matrix.matrix[height_idx][weight_idx]
    assert corr == pytest.approx(1.0, abs=1e-3)

    # Markdown summary check
    assert report.summary_markdown is not None
    assert "# Data Analysis Summary" in report.summary_markdown
    assert "height" in report.summary_markdown
