"""Tests for CodeVerificationTool."""

from xeren.plugins.coding.schemas import FileArtifact, VerificationStatus
from xeren.plugins.coding.tools.verification import CodeVerificationTool


def test_verification_passed():
    """Verify clean code passes all verification stages."""
    tool = CodeVerificationTool()
    code = "def multiply(x: int, y: int) -> int: return x * y"
    test = """
import unittest
from main import multiply

class TestMul(unittest.TestCase):
    def test_mul(self):
        self.assertEqual(multiply(2, 3), 6)

if __name__ == '__main__':
    unittest.main()
"""
    result = tool.verify(source_code=code, test_code=test)
    assert result.status == VerificationStatus.PASSED
    assert result.syntax_ok is True
    assert result.analysis_ok is True
    assert result.tests_ok is True


def test_verification_syntax_failure():
    """Verify syntax errors trigger verification failure."""
    tool = CodeVerificationTool()
    code = "def broken( return x"
    result = tool.verify(source_code=code)
    assert result.status == VerificationStatus.FAILED
    assert result.syntax_ok is False
    assert len(result.diagnostics) >= 1


def test_verification_security_warning():
    """Verify security smells trigger WARNING status."""
    tool = CodeVerificationTool()
    code = "def run_dynamic(cmd): return eval(cmd)"
    result = tool.verify(source_code=code)
    assert result.status == VerificationStatus.WARNING
    assert result.syntax_ok is True
    assert result.analysis_ok is False
    assert len(result.diagnostics) >= 1
    assert any("eval()" in d.message for d in result.diagnostics)


def test_verification_test_failure():
    """Verify failing unit tests trigger verification failure."""
    tool = CodeVerificationTool()
    code = "def add(a, b): return a - b"  # intentional bug
    test = """
import unittest
from main import add

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 2), 4)

if __name__ == '__main__':
    unittest.main()
"""
    result = tool.verify(source_code=code, test_code=test)
    assert result.status == VerificationStatus.FAILED
    assert result.tests_ok is False
