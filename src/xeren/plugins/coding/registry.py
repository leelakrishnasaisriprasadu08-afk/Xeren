"""Tool registry coordinating coding intelligence and execution sandbox tools."""

from typing import Optional

from xeren.models.base import BaseLLM
from xeren.models.providers.mock import MockLLM
from xeren.plugins.coding.tools.analysis import CodeAnalysisTool
from xeren.plugins.coding.tools.diagnostics import DiagnosticsTool
from xeren.plugins.coding.tools.execution import (
    BaseCodeExecutor,
    SubprocessSandboxExecutor,
)
from xeren.plugins.coding.tools.generation import CodeGenerationTool
from xeren.plugins.coding.tools.syntax import SyntaxCheckTool
from xeren.plugins.coding.tools.testing import TestRunnerTool
from xeren.plugins.coding.tools.verification import CodeVerificationTool


class CodingToolRegistry:
    """Central registry aggregating coding, sandbox, and verification tools."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        executor: Optional[BaseCodeExecutor] = None,
        syntax_tool: Optional[SyntaxCheckTool] = None,
        analysis_tool: Optional[CodeAnalysisTool] = None,
        generation_tool: Optional[CodeGenerationTool] = None,
        testing_tool: Optional[TestRunnerTool] = None,
        diagnostics_tool: Optional[DiagnosticsTool] = None,
        verification_tool: Optional[CodeVerificationTool] = None,
    ) -> None:
        self.llm = llm or MockLLM()
        self.executor = executor or SubprocessSandboxExecutor()

        self.syntax_tool = syntax_tool or SyntaxCheckTool()
        self.analysis_tool = analysis_tool or CodeAnalysisTool()
        self.generation_tool = generation_tool or CodeGenerationTool(llm=self.llm)
        self.testing_tool = testing_tool or TestRunnerTool(executor=self.executor)
        self.diagnostics_tool = diagnostics_tool or DiagnosticsTool()
        self.verification_tool = verification_tool or CodeVerificationTool(
            syntax_tool=self.syntax_tool,
            analysis_tool=self.analysis_tool,
            test_runner=self.testing_tool,
        )

    def set_llm(self, llm: BaseLLM) -> None:
        """Update active LLM across the registry."""
        self.llm = llm
        self.generation_tool.set_llm(llm)

    def set_executor(self, executor: BaseCodeExecutor) -> None:
        """Update active code executor across the registry."""
        self.executor = executor
        self.testing_tool.executor = executor


__all__ = ["CodingToolRegistry"]
