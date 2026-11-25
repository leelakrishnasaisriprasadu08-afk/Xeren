"""Tests for FileWorkflow: end-to-end routing of all 10 operations, latency tracking, and error isolation."""

import pytest

from xeren.plugins.file.registry import FileToolRegistry
from xeren.plugins.file.schemas import FileInput, FileOperation, FileResult
from xeren.plugins.file.workflow import FileWorkflow


def test_workflow_all_ten_operations_sync(tmp_path):
    """Verify all 10 operations execute successfully through FileWorkflow."""
    registry = FileToolRegistry(workspace_dir=tmp_path)
    wf = FileWorkflow(registry=registry)

    # 1. CREATE
    res_create = wf.run(FileInput(operation=FileOperation.CREATE, path="doc.txt", content="initial content"))
    assert res_create.success is True
    assert res_create.operation == FileOperation.CREATE
    assert "latency_ms" in res_create.stats

    # 2. READ
    res_read = wf.run(FileInput(operation=FileOperation.READ, path="doc.txt"))
    assert res_read.success is True
    assert res_read.content == "initial content"

    # 3. WRITE
    res_write = wf.run(FileInput(operation=FileOperation.WRITE, path="doc.txt", content="updated content", overwrite=True))
    assert res_write.success is True

    # 4. MODIFY
    res_mod = wf.run(FileInput(operation=FileOperation.MODIFY, path="doc.txt", target_content="updated", replacement="modified"))
    assert res_mod.success is True

    # 5. METADATA
    res_meta = wf.run(FileInput(operation=FileOperation.METADATA, path="doc.txt"))
    assert res_meta.success is True
    assert res_meta.metadata is not None
    assert res_meta.metadata.is_file is True

    # 6. COPY
    res_copy = wf.run(FileInput(operation=FileOperation.COPY, path="doc.txt", destination_path="doc_copy.txt"))
    assert res_copy.success is True

    # 7. MOVE
    res_move = wf.run(FileInput(operation=FileOperation.MOVE, path="doc_copy.txt", destination_path="doc_moved.txt"))
    assert res_move.success is True

    # 8. LIST
    res_list = wf.run(FileInput(operation=FileOperation.LIST, path="."))
    assert res_list.success is True
    assert len(res_list.items) >= 2

    # 9. SEARCH
    res_search = wf.run(FileInput(operation=FileOperation.SEARCH, pattern="*.txt", search_content="modified"))
    assert res_search.success is True
    assert len(res_search.search_results) >= 1

    # 10. DELETE
    res_del = wf.run(FileInput(operation=FileOperation.DELETE, path="doc_moved.txt"))
    assert res_del.success is True


@pytest.mark.asyncio
async def test_workflow_async_run(tmp_path):
    """Verify asynchronous operation routing."""
    registry = FileToolRegistry(workspace_dir=tmp_path)
    wf = FileWorkflow(registry=registry)

    res = await wf.arun(FileInput(operation=FileOperation.CREATE, path="async_file.txt", content="async data"))
    assert res.success is True
    assert res.path == "async_file.txt"


def test_workflow_error_isolation(tmp_path):
    """Verify workflow captures errors safely into FileResult rather than crashing."""
    registry = FileToolRegistry(workspace_dir=tmp_path)
    wf = FileWorkflow(registry=registry)

    # Missing path
    res = wf.run(FileInput(operation=FileOperation.READ, path=None))
    assert res.success is False
    assert "Path is required" in (res.error or "")

    # Nonexistent file
    res_missing = wf.run(FileInput(operation=FileOperation.READ, path="does_not_exist.txt"))
    assert res_missing.success is False
    assert "does not exist" in (res_missing.error or "").lower() or "not found" in (res_missing.error or "").lower()
