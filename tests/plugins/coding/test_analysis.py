"""Tests for CodeAnalysisTool."""

from xeren.plugins.coding.tools.analysis import CodeAnalysisTool


def test_code_analysis_structural_metrics():
    """Verify function, class, and import extraction on Python code."""
    tool = CodeAnalysisTool()
    code = """
import os
from pathlib import Path

class DataProcessor:
    def __init__(self, name: str):
        self.name = name

    def process(self, items: list) -> int:
        count = 0
        for item in items:
            if item > 0:
                count += 1
        return count

def helper_func():
    pass
"""
    report = tool.analyze(code, language="python")
    assert report.lines_of_code > 10
    assert report.classes_count == 1
    assert report.functions_count == 3  # __init__, process, helper_func
    assert "os" in report.imports
    assert "pathlib.Path" in report.imports
    assert report.complexity_score > 1.0
    assert len(report.security_warnings) == 0


def test_security_smell_detection_eval_exec():
    """Verify dangerous eval and exec calls are flagged."""
    tool = CodeAnalysisTool()
    code = """
user_input = "__import__('os').system('ls')"
res = eval(user_input)
exec("x = 1")
"""
    report = tool.analyze(code, language="python")
    assert len(report.security_warnings) >= 2
    assert any("eval()" in w for w in report.security_warnings)
    assert any("exec()" in w for w in report.security_warnings)


def test_security_smell_detection_os_system_subprocess():
    """Verify os.system and shell=True subprocess calls are flagged."""
    tool = CodeAnalysisTool()
    code = """
import os
import subprocess

os.system("echo hello")
subprocess.Popen(["echo"], shell=True)
"""
    report = tool.analyze(code, language="python")
    assert len(report.security_warnings) >= 2
    assert any("os.system()" in w for w in report.security_warnings)
    assert any("shell=True" in w for w in report.security_warnings)


def test_generic_analysis_fallback():
    """Verify non-Python code analysis fallback."""
    tool = CodeAnalysisTool()
    code = """
function doWork() {
    eval("console.log('danger')");
}
"""
    report = tool.analyze(code, language="javascript")
    assert report.lines_of_code >= 3
    assert len(report.security_warnings) >= 1
    assert "eval()" in report.security_warnings[0]
