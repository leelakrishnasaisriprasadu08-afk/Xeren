"""Tests for the Royal Triumvirate leadership protocol and deterministic tools."""

import tempfile
from pathlib import Path
import pytest

from xeren.tools.deterministic.fs import DeterministicFileSystem
from xeren.tools.deterministic.system import DeterministicSystemTools
from xeren.tools.deterministic.browser import DeterministicBrowserTools
from xeren.core.leadership import LeadershipTriumvirate, default_triumvirate
from xeren.data.synthesizer import TriumvirateTrajectorySynthesizer, FOUNDATIONAL_TASKS


def test_deterministic_fs_read_write_patch():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fs = DeterministicFileSystem(root_dir=tmp_dir)

        # 1. Write file
        w_res = fs.write_file("test.txt", "line1\nline2\nline3\n")
        assert w_res["success"] is True

        # 2. Read file with line slicing
        r_res = fs.read_file("test.txt", start_line=2, end_line=3)
        assert r_res["success"] is True
        assert r_res["content"] == "line2\nline3\n"

        # 3. Patch file
        p_res = fs.patch_file("test.txt", "line2", "LINE_TWO_MODIFIED")
        assert p_res["success"] is True

        # 4. Verify patch
        v_res = fs.read_file("test.txt")
        assert "LINE_TWO_MODIFIED" in v_res["content"]

        # 5. List dir
        l_res = fs.list_dir(pattern="*.txt")
        assert l_res["success"] is True
        assert l_res["count"] == 1


def test_deterministic_system_execution():
    sys_tools = DeterministicSystemTools()

    # 1. Safe command execution
    res = sys_tools.run_command("python -c \"print('HELLO_DETERMINISTIC')\"")
    assert res["success"] is True
    assert "HELLO_DETERMINISTIC" in res["stdout"]

    # 2. Block dangerous destructive command
    dangerous_res = sys_tools.run_command("format c: /q")
    assert dangerous_res["success"] is False
    assert "blocked by safety boundary" in dangerous_res["error"]

    # 3. System stats
    stats = sys_tools.get_system_stats()
    assert stats["success"] is True
    assert "os" in stats
    assert "python_version" in stats


def test_leadership_triumvirate_deterministic_fastpath():
    tri = default_triumvirate

    # 1. Ask King to read README.md
    response = tri.process("Read the contents of README.md")
    assert response.success is True
    assert "README.md" in response.content or len(str(response.deliverable)) > 10
    assert response.reasoning_summary != ""


def test_triumvirate_trajectory_synthesizer():
    with tempfile.TemporaryDirectory() as tmp_dir:
        synth = TriumvirateTrajectorySynthesizer(output_dir=Path(tmp_dir))
        out_file = synth.export_dataset(FOUNDATIONAL_TASKS[:3], filename="test_sft.jsonl")

        assert out_file.exists()
        lines = [line.strip() for line in open(out_file, encoding="utf-8") if line.strip()]
        assert len(lines) == 3

