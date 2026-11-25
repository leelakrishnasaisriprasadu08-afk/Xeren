"""
test_workstation_automation.py
==============================
Test suite for the WorkstationAutomator: verified file editing, symbol search, and system actions.
"""

import tempfile
import pytest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from xeren.automation.workstation import WorkstationAutomator, default_automator


def test_workstation_verified_edit_success():
    """Verify that valid python edits succeed with AST validation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_py = Path(tmp_dir) / "sample.py"
        test_py.write_text("def greet():\n    return 'hello'\n", encoding="utf-8")

        automator = WorkstationAutomator()
        res = automator.edit_file_verified(
            file_path=test_py,
            search_block="return 'hello'",
            replace_block="return 'welcome to xeren'",
        )

        assert res["success"] is True
        assert "AST/Syntax check passed" in res["verification"]
        assert "welcome to xeren" in test_py.read_text(encoding="utf-8")


def test_workstation_verified_edit_rollback_on_syntax_error():
    """Verify that invalid syntax triggers an automatic rollback preserving file integrity."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_py = Path(tmp_dir) / "safe_script.py"
        original = "def calculate(x):\n    return x * 2\n"
        test_py.write_text(original, encoding="utf-8")

        automator = WorkstationAutomator()
        # Attempt to insert malformed syntax (missing parenthesis / broken statement)
        res = automator.edit_file_verified(
            file_path=test_py,
            search_block="return x * 2",
            replace_block="return (x * 2 def invalid",
        )

        assert res["success"] is False
        assert res.get("rolled_back") is True
        assert "Syntax verification failed" in res["error"]
        # File contents must remain completely unchanged!
        assert test_py.read_text(encoding="utf-8") == original


def test_workstation_find_symbol():
    """Verify that codebase symbol search locates functions across files."""
    automator = WorkstationAutomator()
    # Search for an existing class in src/xeren
    matches = automator.find_symbol("WorkstationAutomator", root_dir="src/xeren")
    assert len(matches) > 0
    assert any("class" in m["kind"] for m in matches)
    assert any("workstation.py" in m["file"] for m in matches)


def test_workstation_system_telemetry():
    """Verify that system stats and top processes are returned safely."""
    automator = WorkstationAutomator()
    metrics = automator.get_system_metrics()
    assert metrics["success"] is True
    assert "os" in metrics
    assert "architecture" in metrics

    procs = automator.list_top_processes(limit=5)
    assert isinstance(procs, list)
