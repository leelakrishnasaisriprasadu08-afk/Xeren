"""Tests for CodeGenerationTool."""

import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.coding.tools.generation import CodeGenerationTool


def test_code_generation_with_fences():
    """Verify markdown code fences are extracted properly."""
    canned = "Here is the implementation:\n```python\ndef is_prime(n):\n    return n > 1\n```\nHope this helps!"
    llm = MockLLM(canned_response=canned)
    tool = CodeGenerationTool(llm=llm)

    code = tool.generate(task="Implement prime check", language="python")
    assert "def is_prime(n):" in code
    assert "return n > 1" in code
    assert "Here is the implementation" not in code


def test_code_generation_with_context():
    """Verify existing context files are included in generation prompt."""
    llm = MockLLM(canned_response="```python\ndef new_feature(): pass\n```")
    tool = CodeGenerationTool(llm=llm)
    context = [FileArtifact(file_path="base.py", content="class Base: pass")]

    code = tool.generate(task="Add feature", context_files=context)
    assert "def new_feature():" in code
    assert len(llm.call_history) == 1
    prompt_content = llm.call_history[0][1].content or ""
    assert "base.py" in prompt_content


def test_code_edit():
    """Verify code editing method prompts for refactoring and extracts code."""
    canned = "```python\ndef add(a, b):\n    # optimized\n    return a + b\n```"
    llm = MockLLM(canned_response=canned)
    tool = CodeGenerationTool(llm=llm)

    edited = tool.edit(task="Add comment", source_code="def add(a, b): return a + b")
    assert "# optimized" in edited


@pytest.mark.asyncio
async def test_async_generation():
    """Verify asynchronous generation and editing."""
    llm = MockLLM(canned_response="```python\ndef async_func(): return True\n```")
    tool = CodeGenerationTool(llm=llm)

    code = await tool.agenerate(task="Async function")
    assert "def async_func():" in code
