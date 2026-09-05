"""Tests for CodingWorkflow and operation dispatching."""

import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.registry import CodingToolRegistry
from xeren.plugins.coding.schemas import CodingInput, CodingOperation
from xeren.plugins.coding.workflow import CodingWorkflow
from xeren.plugins.errors import PluginExecutionError


def test_workflow_generate():
    """Verify workflow generates code and verifies syntax."""
    canned = "```python\ndef greet(name: str) -> str:\n    return f'Hello {name}'\n```"
    llm = MockLLM(canned_response=canned)
    registry = CodingToolRegistry(llm=llm)
    wf = CodingWorkflow(registry=registry)

    inp = CodingInput(task="Write greeting function", operation=CodingOperation.GENERATE)
    res = wf.run(inp)

    assert res.operation == CodingOperation.GENERATE
    assert res.success is True
    assert res.syntax_valid is True
    assert len(res.files) == 1
    assert "def greet" in res.files[0].content


def test_workflow_analyze_and_syntax_check():
    """Verify workflow static analysis and syntax checking."""
    wf = CodingWorkflow()
    code = "import math\ndef calc(r): return math.pi * r * r"

    analyze_inp = CodingInput(operation=CodingOperation.ANALYZE, source_code=code)
    analyze_res = wf.run(analyze_inp)
    assert analyze_res.analysis is not None
    assert analyze_res.analysis.functions_count == 1

    syntax_inp = CodingInput(operation=CodingOperation.SYNTAX_CHECK, source_code=code)
    syntax_res = wf.run(syntax_inp)
    assert syntax_res.syntax_valid is True


def test_workflow_execute_and_test():
    """Verify workflow code execution and unit testing."""
    wf = CodingWorkflow()
    exec_inp = CodingInput(
        operation=CodingOperation.EXECUTE,
        source_code="print('Execution test output')",
    )
    exec_res = wf.run(exec_inp)
    assert exec_res.success is True
    assert exec_res.execution_output is not None
    assert "Execution test output" in exec_res.execution_output.stdout

    test_inp = CodingInput(
        operation=CodingOperation.TEST,
        source_code="def sub(a, b): return a - b",
        test_code="""
import unittest
from main import sub
class TestSub(unittest.TestCase):
    def test_sub(self):
        self.assertEqual(sub(5, 2), 3)
if __name__ == '__main__':
    unittest.main()
""",
    )
    test_res = wf.run(test_inp)
    assert test_res.success is True
    assert test_res.test_summary is not None
    assert test_res.test_summary.passed == 1


@pytest.mark.asyncio
async def test_workflow_async_run():
    """Verify asynchronous workflow execution."""
    wf = CodingWorkflow()
    inp = CodingInput(
        operation=CodingOperation.SYNTAX_CHECK,
        source_code="value = 42",
    )
    res = await wf.arun(inp)
    assert res.syntax_valid is True


def test_plugin_execute_error_propagation():
    """Verify invalid input raises PluginExecutionError."""
    plugin = CodingPlugin()
    with pytest.raises(PluginExecutionError):
        plugin.execute({"operation": "generate", "task": ""})
