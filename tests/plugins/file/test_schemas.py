"""Tests for File Plugin Pydantic schemas, enums, defaults, and validation."""

import pytest
from pydantic import ValidationError

from xeren.plugins.file.schemas import (
    FileInput,
    FileItemMetadata,
    FileOperation,
    FileResult,
    SearchResultItem,
)


def test_file_operation_enum_members():
    """Verify FileOperation contains exactly the 10 approved operations and no obsolete members."""
    expected = {
        "read", "write", "create", "modify", "delete",
        "list", "search", "move", "copy", "metadata",
    }
    actual = {op.value for op in FileOperation}
    assert actual == expected
    assert len(FileOperation) == 10
    assert not hasattr(FileOperation, "MOVE_COPY")
    assert not hasattr(FileOperation, "FILE_MOVE_COPY")


def test_file_input_defaults():
    """Verify FileInput initializes with safe, documented defaults."""
    inp = FileInput(operation=FileOperation.READ)
    assert inp.operation == FileOperation.READ
    assert inp.path is None
    assert inp.destination_path is None
    assert inp.content is None
    assert inp.encoding == "utf-8"
    assert inp.dry_run is False
    assert inp.redaction_enabled is True
    assert inp.atomic is True
    assert inp.create_parents is True
    assert inp.overwrite is False
    assert inp.recursive is True
    assert inp.include_hidden is False
    assert inp.max_results == 100
    assert inp.metadata == {}


def test_file_input_validation_constraints():
    """Verify bounds and validation errors on FileInput."""
    # max_results < 1 must fail
    with pytest.raises(ValidationError):
        FileInput(operation=FileOperation.LIST, max_results=0)  # type: ignore

    # invalid operation string
    with pytest.raises(ValidationError):
        FileInput(operation="invalid_op")  # type: ignore


def test_file_result_structure():
    """Verify FileResult instantiation and default field values."""
    res = FileResult(operation=FileOperation.WRITE, success=True, path="test.txt", dry_run=True)
    assert res.operation == FileOperation.WRITE
    assert res.success is True
    assert res.path == "test.txt"
    assert res.dry_run is True
    assert res.redacted_secrets is False
    assert res.items == []
    assert res.search_results == []
    assert res.stats == {}


def test_file_item_metadata_and_search_result_schemas():
    """Verify FileItemMetadata and SearchResultItem structures."""
    item = FileItemMetadata(
        path="src/main.py",
        name="main.py",
        size_bytes=1024,
        is_file=True,
        extension=".py",
        is_binary=False,
    )
    assert item.path == "src/main.py"
    assert item.is_file is True
    assert item.size_bytes == 1024

    search_item = SearchResultItem(
        path="src/main.py",
        line_number=42,
        line_content="def start():",
        match_start=4,
        match_end=9,
    )
    assert search_item.line_number == 42
    assert search_item.match_start == 4
