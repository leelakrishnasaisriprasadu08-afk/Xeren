"""Verification tool coordinating multi-stage syntax, analysis, and test checks."""

import logging
from typing import List, Optional, Sequence

from xeren.plugins.coding.schemas import (
    Diagnostic,
    DiagnosticSeverity,
    ExecutionConfig,
    FileArtifact,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.coding.tools.analysis import CodeAnalysisTool
from xeren.plugins.coding.tools.syntax import SyntaxCheckTool
from xeren.plugins.coding.tools.testing import TestRunnerTool

logger = logging.getLogger("xeren.plugins.coding.tools.verification")


class CodeVerificationTool:
    """Coordinates multi-stage verification across syntax, static analysis, and testing."""

    def __init__(
        self,
        syntax_tool: Optional[SyntaxCheckTool] = None,
        analysis_tool: Optional[CodeAnalysisTool] = None,
        test_runner: Optional[TestRunnerTool] = None,
    ) -> None:
        self.syntax_tool = syntax_tool or SyntaxCheckTool()
        self.analysis_tool = analysis_tool or CodeAnalysisTool()
        self.test_runner = test_runner or TestRunnerTool()

    def verify(
        self,
        source_code: Optional[str] = None,
        source_files: Optional[Sequence[FileArtifact]] = None,
        language: str = "python",
        test_code: Optional[str] = None,
        test_command: Optional[str] = None,
        config: Optional[ExecutionConfig] = None,
    ) -> VerificationResult:
        """Execute end-to-end verification pipeline."""
        diagnostics: List[Diagnostic] = []
        files_to_check: List[FileArtifact] = []

        if source_files:
            files_to_check.extend(source_files)
        if source_code:
            files_to_check.append(FileArtifact(file_path="main.py", content=source_code, language=language))

        # 1. Syntax Verification Stage
        syntax_ok = True
        for artifact in files_to_check:
            is_valid, diags = self.syntax_tool.check_syntax(
                code=artifact.content,
                language=artifact.language,
                file_path=artifact.file_path,
            )
            if not is_valid:
                syntax_ok = False
                diagnostics.extend(diags)

        # 2. Static Analysis & Security Stage
        analysis_ok = True
        for artifact in files_to_check:
            report = self.analysis_tool.analyze(artifact.content, language=artifact.language)
            for warning in report.security_warnings:
                analysis_ok = False
                diagnostics.append(
                    Diagnostic(
                        message=warning,
                        severity=DiagnosticSeverity.WARNING,
                        rule_id="security_smell",
                        file_path=artifact.file_path,
                    )
                )

        # 3. Test Execution Stage (if tests provided)
        tests_ok = True
        if test_code or test_command:
            test_summary = self.test_runner.run_tests(
                source_files=files_to_check,
                test_code=test_code,
                test_command=test_command,
                config=config,
            )
            if test_summary.failed > 0 or test_summary.errors > 0:
                tests_ok = False
                diagnostics.append(
                    Diagnostic(
                        message=f"Test suite failed: {test_summary.failed} failure(s), {test_summary.errors} error(s).",
                        severity=DiagnosticSeverity.ERROR,
                        rule_id="test_suite_failure",
                    )
                )

        # Determine aggregate status
        if not syntax_ok or not tests_ok:
            status = VerificationStatus.FAILED
            summary = "Verification failed due to syntax errors or failing unit tests."
        elif not analysis_ok:
            status = VerificationStatus.WARNING
            summary = "Code passed syntax and tests, but security warnings were identified."
        else:
            status = VerificationStatus.PASSED
            summary = "Code successfully passed all syntax, analysis, and verification checks."

        return VerificationResult(
            status=status,
            syntax_ok=syntax_ok,
            analysis_ok=analysis_ok,
            tests_ok=tests_ok,
            summary=summary,
            diagnostics=diagnostics,
        )


__all__ = ["CodeVerificationTool"]
