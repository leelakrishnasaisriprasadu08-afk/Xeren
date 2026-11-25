"""Tests for Core -> PluginManager -> DataPlugin end-to-end integration and multi-plugin coexistence."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.coding.schemas import CodingOperation
from xeren.plugins.data.plugin import DataPlugin
from xeren.plugins.data.schemas import (
    CleaningRule,
    DataOperation,
    DataResult,
    DataValidationRule,
    StructuredDataset,
    TransformConfig,
)
from xeren.plugins.website.schemas import WebsiteOperation


def test_core_auto_registers_data_plugin():
    """Verify XerenCore auto-registers DataPlugin alongside Research, Knowledge, Coding, and Website."""
    core = XerenCore(auto_register_defaults=True)
    assert core.has_plugin("research")
    assert core.has_plugin("knowledge")
    assert core.has_plugin("coding")
    assert core.has_plugin("website")
    assert core.has_plugin("data")

    plugin = core.get_plugin("data")
    assert plugin is not None
    assert plugin.name == "data"


def test_core_execute_plugin_data():
    """Verify core.execute_plugin for data inspection."""
    core = XerenCore()
    exec_res = core.execute_plugin(
        name="data",
        input_data={
            "operation": "inspect",
            "records": [{"col1": 10, "col2": "test"}, {"col1": 20, "col2": "test2"}],
        },
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, DataResult)
    assert exec_res.output.operation == DataOperation.INSPECT
    assert exec_res.output.inspection_report is not None
    assert exec_res.output.inspection_report.row_count == 2


@pytest.mark.asyncio
async def test_core_aexecute_plugin_data():
    """Verify async core.aexecute_plugin for data cleaning."""
    core = XerenCore()
    exec_res = await core.aexecute_plugin(
        name="data",
        input_data={
            "operation": "clean",
            "records": [
                {"id": 1, "txt": "  hello  "},
                {"id": 1, "txt": "  hello  "},
            ],
            "cleaning_rules": [{"rule_type": "drop_duplicates"}, {"rule_type": "trim_strings"}],
        },
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, DataResult)
    assert exec_res.output.dataset is not None
    assert exec_res.output.dataset.row_count() == 1
    assert exec_res.output.dataset.data[0]["txt"] == "hello"


def test_core_data_convenience_methods():
    """Verify core.data convenience method for inspect, transform, and analyze."""
    core = XerenCore()
    dataset = StructuredDataset.from_records([{"x": 10}, {"x": 20}, {"x": 30}])

    # 1. Inspect
    res_inspect = core.data(operation=DataOperation.INSPECT, dataset=dataset)
    assert res_inspect.success is True
    assert res_inspect.inspection_report is not None
    assert res_inspect.inspection_report.column_count == 1

    # 2. Analyze
    res_analyze = core.data(operation=DataOperation.ANALYZE, dataset=dataset)
    assert res_analyze.success is True
    assert res_analyze.analysis_report is not None
    assert res_analyze.analysis_report.total_records == 3
    assert res_analyze.analysis_report.statistics[0].mean == 20.0


@pytest.mark.asyncio
async def test_core_adata_convenience_method():
    """Verify async core.adata convenience method."""
    core = XerenCore()
    dataset = StructuredDataset.from_records([{"score": 90}, {"score": 95}])
    res = await core.adata(operation=DataOperation.INSPECT, dataset=dataset)
    assert res.success is True
    assert res.inspection_report is not None
    assert res.inspection_report.row_count == 2


def test_core_plugin_direct_typed_methods():
    """Verify DataPlugin direct typed helper methods (ingest, inspect, clean, transform, analyze, visualize, verify)."""
    core = XerenCore()
    plugin = core.get_plugin("data")
    assert isinstance(plugin, DataPlugin)

    # Ingest
    ds = plugin.ingest(records=[{"val": 100}, {"val": 200}])
    assert ds.row_count() == 2

    # Inspect
    insp = plugin.inspect(ds)
    assert insp.column_count == 1

    # Clean
    cleaned = plugin.clean(ds, rules=[CleaningRule(rule_type="trim_strings")])
    assert cleaned.row_count() == 2

    # Transform
    transformed = plugin.transform(
        ds,
        config=TransformConfig(filters=[{"column": "val", "operator": ">", "value": 150}]),
    )
    assert transformed.row_count() == 1

    # Analyze
    analysis = plugin.analyze(ds)
    assert analysis.total_records == 2

    # Visualize
    vis = plugin.visualize(ds)
    assert vis.spec is not None

    # Verify
    report = plugin.verify(
        ds,
        rules=[DataValidationRule(rule_name="not_null", column="val")],
    )
    assert report.is_valid is True


def test_core_all_five_plugins_coexistence():
    """Verify Research, Knowledge, Coding, Website, and Data plugins all coexist and function in one Core instance."""
    core = XerenCore()

    # 1. Research Plugin
    res_research = core.research("Data science architectures")
    assert res_research.objective == "Data science architectures"

    # 2. Knowledge Plugin
    core.ingest_knowledge(texts=["Data pipelines require validation and cleaning."])
    res_knowledge = core.knowledge("validation")
    assert len(res_knowledge.retrieved_chunks) >= 1

    # 3. Coding Plugin
    res_coding = core.coding(
        task="Write a function to sum integers",
        operation=CodingOperation.GENERATE,
    )
    assert res_coding.success is True

    # 4. Website Plugin
    res_website = core.website(
        requirement="Create a data analytics dashboard landing page",
        operation=WebsiteOperation.GENERATE,
    )
    assert res_website.success is True

    # 5. Data Plugin
    res_data = core.data(
        operation=DataOperation.INSPECT,
        records=[{"metric": "latency", "ms": 42}],
    )
    assert res_data.success is True
    assert res_data.inspection_report is not None
    assert res_data.inspection_report.row_count == 1

    # Verify all 5 report healthy in core.plugin_health()
    health_map = core.plugin_health()
    assert len(health_map) >= 5
    assert health_map["research"].status.value == "healthy"
    assert health_map["knowledge"].status.value == "healthy"
    assert health_map["coding"].status.value == "healthy"
    assert health_map["website"].status.value == "healthy"
    assert health_map["data"].status.value == "healthy"
