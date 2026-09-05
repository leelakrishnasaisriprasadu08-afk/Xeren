"""Tests for SyntaxCheckTool."""

from xeren.plugins.coding.schemas import DiagnosticSeverity
from xeren.plugins.coding.tools.syntax import SyntaxCheckTool


def test_valid_python_syntax():
    """Verify valid Python code passes syntax check."""
    tool = SyntaxCheckTool()
    code = """
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    valid, diags = tool.check_syntax(code, language="python")
    assert valid is True
    assert len(diags) == 0


def test_invalid_python_syntax():
    """Verify invalid Python code produces structured diagnostic with line and column."""
    tool = SyntaxCheckTool()
    code = """
def broken_func(
    x = 10
    return x
"""
    valid, diags = tool.check_syntax(code, language="python")
    assert valid is False
    assert len(diags) >= 1
    assert diags[0].severity == DiagnosticSeverity.ERROR
    assert diags[0].line is not None
    assert diags[0].rule_id == "python_syntax_error"


def test_bracket_balance_valid():
    """Verify code with properly balanced brackets passes."""
    tool = SyntaxCheckTool()
    code = "const arr = [1, 2, { a: (3 + 4) }];"
    valid, diags = tool.check_syntax(code, language="javascript")
    assert valid is True
    assert len(diags) == 0


def test_bracket_balance_unmatched_closing():
    """Verify unmatched closing bracket is flagged."""
    tool = SyntaxCheckTool()
    code = "const x = (1 + 2];"
    valid, diags = tool.check_syntax(code, language="javascript")
    assert valid is False
    assert len(diags) >= 1
    assert "Unmatched closing delimiter" in diags[0].message


def test_bracket_balance_unclosed_opening():
    """Verify unclosed opening bracket is flagged."""
    tool = SyntaxCheckTool()
    code = "function test() { const y = [1, 2, 3;"
    valid, diags = tool.check_syntax(code, language="javascript")
    assert valid is False
    assert len(diags) >= 1
    assert "Unclosed opening delimiter" in diags[0].message
