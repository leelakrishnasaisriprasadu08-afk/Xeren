"""Tests for Core -> PluginManager -> FilePlugin integration, multi-plugin coexistence, and typed Core helpers."""

from pathlib import Path
import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import CodingOperation
from xeren.plugins.data.schemas import DataOperation
from xeren.plugins.file.plugin import FilePlugin
from xeren.plugins.file.schemas import FileOperation, FileResult
from xeren.plugins.website.schemas import WebsiteOperation


def test_core_auto_registers_file_plugin():
    """Verify XerenCore auto-registers FilePlugin alongside Research, Knowledge, Coding, Website, and Data."""
    core = XerenCore(auto_register_defaults=True)
    assert core.has_plugin("research")
    assert core.has_plugin("knowledge")
    assert core.has_plugin("coding")
    assert core.has_plugin("website")
    assert core.has_plugin("data")
    assert core.has_plugin("file")

    plugin = core.get_plugin("file")
    assert plugin is not None
    assert isinstance(plugin, FilePlugin)
    assert plugin.name == "file"


def test_core_execute_plugin_file(tmp_path):
    """Verify core.execute_plugin for file write and read."""
    core = XerenCore()
    plugin = core.get_plugin("file")
    assert isinstance(plugin, FilePlugin)
    plugin.set_workspace_dir(tmp_path)

    # 1. Write
    write_res = core.execute_plugin(
        name="file",
        input_data={
            "operation": "write",
            "path": "core_test.txt",
            "content": "Hello from Core execution",
            "overwrite": True,
        },
    )
    assert write_res.success is True
    assert isinstance(write_res.output, FileResult)

    # 2. Read
    read_res = core.execute_plugin(
        name="file",
        input_data={
            "operation": "read",
            "path": "core_test.txt",
        },
    )
    assert read_res.success is True
    assert isinstance(read_res.output, FileResult)
    assert read_res.output.content == "Hello from Core execution"


@pytest.mark.asyncio
async def test_core_aexecute_plugin_file(tmp_path):
    """Verify async core.aexecute_plugin for file operations."""
    core = XerenCore()
    plugin = core.get_plugin("file")
    assert isinstance(plugin, FilePlugin)
    plugin.set_workspace_dir(tmp_path)

    exec_res = await core.aexecute_plugin(
        name="file",
        input_data={
            "operation": "create",
            "path": "async_core.txt",
            "content": "Async Core Data",
        },
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, FileResult)
    assert (tmp_path / "async_core.txt").read_text(encoding="utf-8") == "Async Core Data"


def test_core_file_convenience_helpers(tmp_path):
    """Verify core.file(), core.read_file(), core.write_file(), and core.list_files()."""
    core = XerenCore()
    plugin = core.get_plugin("file")
    assert isinstance(plugin, FilePlugin)
    plugin.set_workspace_dir(tmp_path)

    # 1. core.write_file
    res_w = core.write_file("helper.txt", content="Helper text", overwrite=True)
    assert res_w.success is True

    # 2. core.read_file
    res_r = core.read_file("helper.txt")
    assert res_r.success is True
    assert res_r.content == "Helper text"

    # 3. core.list_files
    items = core.list_files()
    assert len(items) >= 1
    assert any(i.name == "helper.txt" for i in items)

    # 4. core.file general method
    meta_res = core.file(operation=FileOperation.METADATA, path="helper.txt")
    assert meta_res.success is True
    assert meta_res.metadata is not None
    assert meta_res.metadata.is_file is True


@pytest.mark.asyncio
async def test_core_afile_convenience_method(tmp_path):
    """Verify async core.afile convenience method."""
    core = XerenCore()
    plugin = core.get_plugin("file")
    assert isinstance(plugin, FilePlugin)
    plugin.set_workspace_dir(tmp_path)

    res = await core.afile(operation=FileOperation.WRITE, path="async_helper.txt", content="Content", overwrite=True)
    assert res.success is True
    assert (tmp_path / "async_helper.txt").exists()


def test_core_all_six_plugins_coexistence(tmp_path):
    """Verify Research, Knowledge, Coding, Website, Data, and File plugins all coexist and function in one Core."""
    core = XerenCore()

    # Configure FilePlugin workspace
    file_plugin = core.get_plugin("file")
    assert isinstance(file_plugin, FilePlugin)
    file_plugin.set_workspace_dir(tmp_path)

    # 1. Research
    res_research = core.research("System design principles")
    assert res_research.objective == "System design principles"

    # 2. Knowledge
    core.ingest_knowledge(texts=["Xeren implements 6 modular plugins."])
    res_knowledge = core.knowledge("plugins")
    assert len(res_knowledge.retrieved_chunks) >= 1

    # 3. Coding
    res_coding = core.coding(
        task="Write a greet function",
        operation=CodingOperation.GENERATE,
    )
    assert res_coding.success is True

    # 4. Website
    res_website = core.website(
        requirement="Create landing page",
        operation=WebsiteOperation.GENERATE,
    )
    assert res_website.success is True

    # 5. Data
    res_data = core.data(
        operation=DataOperation.INSPECT,
        records=[{"score": 100}],
    )
    assert res_data.success is True

    # 6. File
    res_file = core.write_file("coexist.txt", content="Coexistence verified", overwrite=True)
    assert res_file.success is True
    assert core.read_file("coexist.txt").content == "Coexistence verified"

    # Verify all report healthy
    health_map = core.plugin_health()
    assert len(health_map) >= 6
    assert health_map["research"].status.value == "healthy"
    assert health_map["knowledge"].status.value == "healthy"
    assert health_map["coding"].status.value == "healthy"
    assert health_map["website"].status.value == "healthy"
    assert health_map["data"].status.value == "healthy"
    assert health_map["file"].status.value == "healthy"


def test_file_plugin_does_not_execute_code(tmp_path):
    """Verify FilePlugin has zero code execution capability and does not execute files."""
    core = XerenCore()
    file_plugin = core.get_plugin("file")
    assert isinstance(file_plugin, FilePlugin)

    # Verify file plugin has no execute_code or sandbox methods
    assert not hasattr(file_plugin, "execute_code")
    assert not hasattr(file_plugin, "sandbox")
    assert not hasattr(file_plugin, "run_command")

    # CodingPlugin remains responsible for code execution
    coding_plugin = core.get_plugin("coding")
    assert isinstance(coding_plugin, CodingPlugin)
    assert hasattr(coding_plugin.registry, "executor")
