"""Coding workflow orchestrating generation, analysis, sandbox execution, testing, and verification."""

import asyncio
import logging
import sys
import time
from typing import Any, Dict, List, Optional

from xeren.plugins.coding.registry import CodingToolRegistry
from xeren.plugins.coding.schemas import (
    CodeAnalysisReport,
    CodingInput,
    CodingOperation,
    CodingResult,
    Diagnostic,
    ExecutionOutput,
    FileArtifact,
    TestSummary,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.coding.tools.execution import SubprocessSandboxExecutor

logger = logging.getLogger("xeren.plugins.coding.workflow")


class CodingWorkflow:
    """Coordinates coding tools to execute requested operations safely."""

    def __init__(self, registry: Optional[CodingToolRegistry] = None) -> None:
        self.registry = registry or CodingToolRegistry()

    # -------------------------------------------------------------------------
    # Operation Handlers
    # -------------------------------------------------------------------------
    def execute_generate(self, input_data: CodingInput) -> CodingResult:
        """Generate new code according to instruction, then validate syntax and analyze."""
        start_time = time.perf_counter()

        generated_code = self.registry.generation_tool.generate(
            task=input_data.task,
            language=input_data.language,
            context_files=input_data.source_files,
        )

        entrypoint = input_data.entrypoint or ("main.py" if input_data.language.lower() == "python" else "index.js")
        generated_file = FileArtifact(
            file_path=entrypoint,
            content=generated_code,
            language=input_data.language,
        )

        # Validate syntax
        is_valid, diagnostics = self.registry.syntax_tool.check_syntax(
            code=generated_code,
            language=input_data.language,
            file_path=entrypoint,
        )

        # Perform static analysis
        analysis = self.registry.analysis_tool.analyze(generated_code, language=input_data.language)

        # Run verification if test code was provided
        verification: Optional[VerificationResult] = None
        if input_data.test_code or input_data.test_command:
            verification = self.registry.verification_tool.verify(
                source_files=[generated_file],
                language=input_data.language,
                test_code=input_data.test_code,
                test_command=input_data.test_command,
                config=input_data.execution_config,
            )
            diagnostics.extend(verification.diagnostics)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return CodingResult(
            operation=CodingOperation.GENERATE,
            task=input_data.task,
            language=input_data.language,
            files=[generated_file],
            diagnostics=diagnostics,
            syntax_valid=is_valid,
            analysis=analysis,
            verification=verification,
            execution_stats={"latency_ms": latency_ms},
            success=is_valid and (verification.status != VerificationStatus.FAILED if verification else True),
        )

    def execute_edit(self, input_data: CodingInput) -> CodingResult:
        """Modify existing source code according to instruction."""
        start_time = time.perf_counter()
        source = input_data.source_code or (input_data.source_files[0].content if input_data.source_files else "")

        modified_code = self.registry.generation_tool.edit(
            task=input_data.task,
            source_code=source,
            language=input_data.language,
        )

        entrypoint = input_data.entrypoint or "modified_code.py"
        modified_file = FileArtifact(
            file_path=entrypoint,
            content=modified_code,
            language=input_data.language,
        )

        is_valid, diagnostics = self.registry.syntax_tool.check_syntax(
            code=modified_code,
            language=input_data.language,
            file_path=entrypoint,
        )
        analysis = self.registry.analysis_tool.analyze(modified_code, language=input_data.language)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return CodingResult(
            operation=CodingOperation.EDIT,
            task=input_data.task,
            language=input_data.language,
            files=[modified_file],
            diagnostics=diagnostics,
            syntax_valid=is_valid,
            analysis=analysis,
            execution_stats={"latency_ms": latency_ms},
            success=is_valid,
        )

    def execute_analyze(self, input_data: CodingInput) -> CodingResult:
        """Perform static analysis on provided code or files."""
        start_time = time.perf_counter()
        code = input_data.source_code or (input_data.source_files[0].content if input_data.source_files else "")
        analysis = self.registry.analysis_tool.analyze(code, language=input_data.language)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        diagnostics: List[Diagnostic] = []
        for warning in analysis.security_warnings:
            diagnostics.append(
                Diagnostic(
                    message=warning,
                    rule_id="security_warning",
                )
            )

        return CodingResult(
            operation=CodingOperation.ANALYZE,
            task=input_data.task,
            language=input_data.language,
            files=input_data.source_files,
            diagnostics=diagnostics,
            syntax_valid=True,
            analysis=analysis,
            execution_stats={"latency_ms": latency_ms},
            success=True,
        )

    def execute_syntax_check(self, input_data: CodingInput) -> CodingResult:
        """Validate syntax of code or source files."""
        start_time = time.perf_counter()
        all_diags: List[Diagnostic] = []
        all_valid = True

        files = list(input_data.source_files)
        if input_data.source_code:
            files.append(FileArtifact(file_path="main.py", content=input_data.source_code, language=input_data.language))

        for f in files:
            valid, diags = self.registry.syntax_tool.check_syntax(f.content, language=f.language, file_path=f.file_path)
            if not valid:
                all_valid = False
            all_diags.extend(diags)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return CodingResult(
            operation=CodingOperation.SYNTAX_CHECK,
            task=input_data.task,
            language=input_data.language,
            files=files,
            diagnostics=all_diags,
            syntax_valid=all_valid,
            execution_stats={"latency_ms": latency_ms},
            success=all_valid,
        )

    def execute_code(self, input_data: CodingInput) -> CodingResult:
        """Safely execute code within the isolated sandbox."""
        start_time = time.perf_counter()
        files = list(input_data.source_files)
        entrypoint = input_data.entrypoint or "main.py"

        if input_data.source_code:
            files.append(FileArtifact(file_path=entrypoint, content=input_data.source_code, language=input_data.language))

        cfg = input_data.execution_config
        sandbox = self.registry.executor if isinstance(self.registry.executor, SubprocessSandboxExecutor) else SubprocessSandboxExecutor()

        with sandbox.isolated_workspace(files=files, custom_dir=cfg.working_dir) as workspace:
            python_exe = sys.executable or "python"
            command = [python_exe, entrypoint]
            exec_out = self.registry.executor.execute(command, working_dir=workspace, config=cfg)

        diagnostics: List[Diagnostic] = []
        if exec_out.stderr:
            diagnostics = self.registry.diagnostics_tool.diagnose_traceback(exec_out.stderr)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        success = (exec_out.exit_code == 0 and not exec_out.timed_out)

        return CodingResult(
            operation=CodingOperation.EXECUTE,
            task=input_data.task,
            language=input_data.language,
            files=files,
            diagnostics=diagnostics,
            execution_output=exec_out,
            execution_stats={"latency_ms": latency_ms},
            success=success,
            error=exec_out.error_message if not success else None,
        )

    def execute_test(self, input_data: CodingInput) -> CodingResult:
        """Execute test suites inside the sandbox."""
        start_time = time.perf_counter()
        files = list(input_data.source_files)
        if input_data.source_code:
            entrypoint = input_data.entrypoint or "main.py"
            files.append(FileArtifact(file_path=entrypoint, content=input_data.source_code, language=input_data.language))

        summary = self.registry.testing_tool.run_tests(
            source_files=files,
            test_code=input_data.test_code,
            test_command=input_data.test_command,
            config=input_data.execution_config,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        success = (summary.failed == 0 and summary.errors == 0)

        diagnostics: List[Diagnostic] = []
        if not success and summary.raw_output:
            diagnostics = self.registry.diagnostics_tool.diagnose_traceback(summary.raw_output)

        return CodingResult(
            operation=CodingOperation.TEST,
            task=input_data.task,
            language=input_data.language,
            files=files,
            diagnostics=diagnostics,
            test_summary=summary,
            execution_stats={"latency_ms": latency_ms},
            success=success,
            error=f"Tests failed: {summary.failed} failure(s), {summary.errors} error(s)" if not success else None,
        )

    def execute_verify(self, input_data: CodingInput) -> CodingResult:
        """Run multi-stage verification across syntax, analysis, and execution."""
        start_time = time.perf_counter()
        verification = self.registry.verification_tool.verify(
            source_code=input_data.source_code,
            source_files=input_data.source_files,
            language=input_data.language,
            test_code=input_data.test_code,
            test_command=input_data.test_command,
            config=input_data.execution_config,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        success = (verification.status != VerificationStatus.FAILED)

        return CodingResult(
            operation=CodingOperation.VERIFY,
            task=input_data.task,
            language=input_data.language,
            files=input_data.source_files,
            diagnostics=verification.diagnostics,
            syntax_valid=verification.syntax_ok,
            verification=verification,
            execution_stats={"latency_ms": latency_ms},
            success=success,
            error=verification.summary if not success else None,
        )

    # -------------------------------------------------------------------------
    # Main Workflow Dispatcher
    # -------------------------------------------------------------------------
    def run(self, input_data: CodingInput) -> CodingResult:
        """Dispatch execution based on the requested coding operation."""
        op = input_data.operation
        if op == CodingOperation.GENERATE:
            return self.execute_generate(input_data)
        elif op == CodingOperation.EDIT:
            return self.execute_edit(input_data)
        elif op == CodingOperation.ANALYZE:
            return self.execute_analyze(input_data)
        elif op == CodingOperation.SYNTAX_CHECK:
            return self.execute_syntax_check(input_data)
        elif op == CodingOperation.EXECUTE:
            return self.execute_code(input_data)
        elif op == CodingOperation.TEST:
            return self.execute_test(input_data)
        elif op == CodingOperation.VERIFY:
            return self.execute_verify(input_data)
        return self.execute_generate(input_data)

    async def arun(self, input_data: CodingInput) -> CodingResult:
        """Asynchronously dispatch execution based on the requested coding operation."""
        return await asyncio.to_thread(self.run, input_data)


__all__ = ["CodingWorkflow"]
