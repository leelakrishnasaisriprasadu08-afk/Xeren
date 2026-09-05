"""Tests for TestRunnerTool."""

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.coding.tools.testing import TestRunnerTool


def test_run_passing_unit_tests():
    """Verify test runner executes and parses passing Python unit tests."""
    runner = TestRunnerTool()
    source_files = [
        FileArtifact(file_path="calculator.py", content="def add(a, b): return a + b\ndef sub(a, b): return a - b")
    ]
    test_code = """
import unittest
from calculator import add, sub

class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_sub(self):
        self.assertEqual(sub(5, 3), 2)

if __name__ == '__main__':
    unittest.main()
"""
    summary = runner.run_tests(source_files=source_files, test_code=test_code)
    assert summary.passed == 2
    assert summary.failed == 0
    assert summary.errors == 0
    assert summary.total == 2


def test_run_failing_unit_tests():
    """Verify test runner parses failing test results."""
    runner = TestRunnerTool()
    source_files = [
        FileArtifact(file_path="math_mod.py", content="def mul(a, b): return a + b")  # intentional bug
    ]
    test_code = """
import unittest
from math_mod import mul

class TestMath(unittest.TestCase):
    def test_mul(self):
        self.assertEqual(mul(3, 4), 12)

if __name__ == '__main__':
    unittest.main()
"""
    summary = runner.run_tests(source_files=source_files, test_code=test_code)
    assert summary.failed >= 1
    assert summary.passed == 0


def test_parse_pytest_output():
    """Verify pytest output format parser."""
    runner = TestRunnerTool()
    pytest_stdout = "= 5 passed, 2 failed, 1 error, 1 skipped in 1.45s ="
    summary = runner.parse_test_output(pytest_stdout, "", duration_ms=1450.0)
    assert summary.passed == 5
    assert summary.failed == 2
    assert summary.errors == 1
    assert summary.skipped == 1
    assert summary.total == 9
