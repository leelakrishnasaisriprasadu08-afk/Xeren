"""Controlled test runner tool executing tests within the sandbox."""

import logging
from pathlib import Path
import re
import sys
from typing import List, Optional, Sequence

from xeren.plugins.coding.schemas import (
    ExecutionConfig,
    FileArtifact,
    TestCaseResult,
    TestStatus,
    TestSummary,
)
from xeren.plugins.coding.tools.execution import (
    BaseCodeExecutor,
    SubprocessSandboxExecutor,
)

logger = logging.getLogger("xeren.plugins.coding.tools.testing")


class TestRunnerTool:
    """Executes test suites within sandbox boundary and parses structured test results."""

    __test__ = False

    def __init__(self, executor: Optional[BaseCodeExecutor] = None) -> None:
        self.executor = executor or SubprocessSandboxExecutor()

    def _parse_unittest_output(self, output: str, duration_ms: float) -> TestSummary:
        """Parse standard Python unittest stderr/stdout text."""
        total = 0
        failed = 0
        errors = 0
        cases: List[TestCaseResult] = []

        # Find "Ran X tests in Ys"
        ran_match = re.search(r"Ran (\d+) test[s]? in ([\d\.]+)s", output)
        if ran_match:
            total = int(ran_match.group(1))

        # Check for FAILED (failures=X, errors=Y)
        failed_match = re.search(r"FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?\)", output)
        if failed_match:
            failed = int(failed_match.group(1) or 0)
            errors = int(failed_match.group(2) or 0)

        # Check for OK
        if "OK" in output and (failed == 0 and errors == 0):
            passed = total
        else:
            passed = max(0, total - failed - errors)

        return TestSummary(
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=0,
            total=total,
            duration_ms=duration_ms,
            cases=cases,
            raw_output=output,
        )

    def _parse_pytest_output(self, output: str, duration_ms: float) -> TestSummary:
        """Parse pytest summary lines."""
        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        # Pattern: "= 2 passed, 1 failed, 1 error in 0.12s ="
        p_match = re.search(r"(\d+) passed", output)
        f_match = re.search(r"(\d+) failed", output)
        e_match = re.search(r"(\d+) error", output)
        s_match = re.search(r"(\d+) skipped", output)

        if p_match:
            passed = int(p_match.group(1))
        if f_match:
            failed = int(f_match.group(1))
        if e_match:
            errors = int(e_match.group(1))
        if s_match:
            skipped = int(s_match.group(1))

        total = passed + failed + errors + skipped

        return TestSummary(
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            total=total,
            duration_ms=duration_ms,
            raw_output=output,
        )

    def parse_test_output(self, stdout: str, stderr: str, duration_ms: float) -> TestSummary:
        """Parse output from unittest or pytest execution."""
        combined = f"{stdout}\n{stderr}".strip()

        if "Ran " in combined and "test" in combined:
            return self._parse_unittest_output(combined, duration_ms)
        elif "passed" in combined or "failed" in combined or "pytest" in combined.lower():
            return self._parse_pytest_output(combined, duration_ms)

        # Fallback default when no specific test framework markers matched
        return TestSummary(
            passed=0,
            failed=0,
            errors=1 if ("Error" in combined or "Exception" in combined) else 0,
            skipped=0,
            total=0,
            duration_ms=duration_ms,
            raw_output=combined,
        )

    def run_tests(
        self,
        source_files: Sequence[FileArtifact],
        test_code: Optional[str] = None,
        test_command: Optional[str] = None,
        config: Optional[ExecutionConfig] = None,
    ) -> TestSummary:
        """Execute test suite in isolated sandbox and parse results."""
        all_files = list(source_files)
        if test_code:
            all_files.append(FileArtifact(file_path="test_suite.py", content=test_code, language="python"))

        cfg = config or ExecutionConfig()
        sandbox = self.executor if isinstance(self.executor, SubprocessSandboxExecutor) else SubprocessSandboxExecutor()

        with sandbox.isolated_workspace(files=all_files, custom_dir=cfg.working_dir) as workspace:
            if test_command:
                cmd_parts = test_command.split()
            else:
                # Default to running unittest on test_suite.py or discover
                python_exe = sys.executable or "python"
                if test_code or (workspace / "test_suite.py").exists():
                    cmd_parts = [python_exe, "-m", "unittest", "test_suite.py"]
                else:
                    cmd_parts = [python_exe, "-m", "unittest", "discover"]

            exec_res = self.executor.execute(cmd_parts, working_dir=workspace, config=cfg)
            summary = self.parse_test_output(
                stdout=exec_res.stdout,
                stderr=exec_res.stderr,
                duration_ms=exec_res.duration_ms,
            )

            # If execution had a nonzero exit code but parser found no failures/errors, mark as error
            if exec_res.exit_code != 0 and summary.failed == 0 and summary.errors == 0:
                summary.errors = 1
                summary.total = max(summary.total, 1)

            return summary


__all__ = ["TestRunnerTool"]
