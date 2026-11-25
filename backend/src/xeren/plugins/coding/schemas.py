"""Schemas for the Xeren Coding Plugin."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class CodingOperation(str, Enum):
    """Supported operation modes for the Coding Plugin."""

    GENERATE = "generate"
    EDIT = "edit"
    ANALYZE = "analyze"
    SYNTAX_CHECK = "syntax_check"
    EXECUTE = "execute"
    TEST = "test"
    VERIFY = "verify"


class DiagnosticSeverity(str, Enum):
    """Severity levels for code diagnostics."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class Diagnostic(BaseModel):
    """Structured code diagnostic message."""

    message: str = Field(..., description="Diagnostic explanation")
    severity: DiagnosticSeverity = Field(default=DiagnosticSeverity.ERROR, description="Diagnostic severity")
    line: Optional[int] = Field(default=None, ge=1, description="1-indexed line number")
    column: Optional[int] = Field(default=None, ge=0, description="0-indexed column offset")
    rule_id: Optional[str] = Field(default=None, description="Identifier of the rule or check")
    file_path: Optional[str] = Field(default=None, description="Relative file path")


class FileArtifact(BaseModel):
    """In-memory or filesystem code artifact."""

    file_path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File text content")
    language: str = Field(default="python", description="Programming language identifier")


class ExecutionConfig(BaseModel):
    """Security and runtime configuration for controlled code execution."""

    timeout_seconds: float = Field(default=10.0, ge=0.1, le=60.0, description="Execution timeout limit")
    max_output_bytes: int = Field(default=102400, ge=1024, le=10485760, description="Max allowed output size (100KB default)")
    allowed_commands: List[str] = Field(
        default_factory=lambda: ["python", "pytest", "node"],
        description="Strict command executable allowlist",
    )
    network_enabled: bool = Field(default=False, description="Whether network egress is permitted (default False)")
    working_dir: Optional[str] = Field(default=None, description="Optional custom working directory")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Custom non-sensitive environment variables")


class ExecutionOutput(BaseModel):
    """Structured output from a controlled subprocess execution."""

    exit_code: int = Field(..., description="Subprocess return code")
    stdout: str = Field(default="", description="Sanitized and redacted standard output")
    stderr: str = Field(default="", description="Sanitized and redacted standard error")
    timed_out: bool = Field(default=False, description="True if execution exceeded timeout")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error explanation if execution failed")


class TestStatus(str, Enum):
    """Status of an individual test case."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestCaseResult(BaseModel):
    """Result of an individual executed test case."""

    __test__ = False

    name: str = Field(..., description="Test case name/identifier")
    status: TestStatus = Field(..., description="Execution outcome")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration")
    failure_message: Optional[str] = Field(default=None, description="Failure description if failed")
    traceback: Optional[str] = Field(default=None, description="Stack traceback if failed or error")


class TestSummary(BaseModel):
    """Aggregated outcome of a test suite run."""

    __test__ = False

    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0.0, ge=0.0)
    cases: List[TestCaseResult] = Field(default_factory=list)
    raw_output: str = Field(default="")


class VerificationStatus(str, Enum):
    """Overall outcome of the multi-stage verification pipeline."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_RUN = "not_run"


class VerificationResult(BaseModel):
    """Detailed outcome of syntax, analysis, and execution verification."""

    status: VerificationStatus = Field(default=VerificationStatus.NOT_RUN)
    syntax_ok: bool = Field(default=True)
    analysis_ok: bool = Field(default=True)
    tests_ok: bool = Field(default=True)
    summary: str = Field(default="")
    diagnostics: List[Diagnostic] = Field(default_factory=list)


class CodeAnalysisReport(BaseModel):
    """Static analysis report inspecting code structure and security."""

    lines_of_code: int = Field(default=0, ge=0)
    functions_count: int = Field(default=0, ge=0)
    classes_count: int = Field(default=0, ge=0)
    imports: List[str] = Field(default_factory=list)
    complexity_score: float = Field(default=1.0, ge=1.0)
    security_warnings: List[str] = Field(default_factory=list)


class CodingInput(BaseModel):
    """Input parameters for Coding Plugin execution."""

    task: str = Field(default="", description="High-level instruction or objective for the coding task")
    operation: CodingOperation = Field(
        default=CodingOperation.GENERATE,
        description="Target coding operation to perform",
    )
    language: str = Field(default="python", description="Programming language (e.g. python, javascript)")
    source_code: Optional[str] = Field(default=None, description="Primary source code snippet")
    source_files: List[FileArtifact] = Field(default_factory=list, description="Project files to inspect or modify")
    entrypoint: Optional[str] = Field(default=None, description="Main file name for execution")
    test_code: Optional[str] = Field(default=None, description="Inline test suite code")
    test_command: Optional[str] = Field(default=None, description="Custom test command (must be in allowlist)")
    execution_config: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Sandbox settings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary caller metadata")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def validate_operation_inputs(self) -> "CodingInput":
        if self.operation in (CodingOperation.GENERATE, CodingOperation.EDIT):
            if not self.task.strip() and not self.source_code:
                raise ValueError("Coding generation/edit operations require a non-empty 'task' or 'source_code'.")
        elif self.operation in (CodingOperation.ANALYZE, CodingOperation.SYNTAX_CHECK):
            if not self.source_code and not self.source_files:
                raise ValueError(f"Coding operation '{self.operation.value}' requires either 'source_code' or 'source_files'.")
        elif self.operation in (CodingOperation.EXECUTE, CodingOperation.TEST):
            if not self.source_code and not self.source_files and not self.test_code:
                raise ValueError(f"Coding operation '{self.operation.value}' requires code to execute or test.")
        return self


class CodingResult(BaseModel):
    """Structured result returned by the Coding Plugin."""

    operation: CodingOperation = Field(..., description="Executed operation mode")
    task: str = Field(default="", description="Original task instruction")
    language: str = Field(default="python", description="Primary programming language")
    files: List[FileArtifact] = Field(default_factory=list, description="Generated or modified file artifacts")
    diagnostics: List[Diagnostic] = Field(default_factory=list, description="Diagnostics, lint, and syntax errors")
    syntax_valid: bool = Field(default=True, description="True if all code passed syntax checks")
    analysis: Optional[CodeAnalysisReport] = Field(default=None, description="Static code analysis report")
    execution_output: Optional[ExecutionOutput] = Field(default=None, description="Subprocess execution output if executed")
    test_summary: Optional[TestSummary] = Field(default=None, description="Aggregated test suite results if tested")
    verification: Optional[VerificationResult] = Field(default=None, description="Multi-stage verification report")
    execution_stats: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics (latency_ms, etc.)")
    success: bool = Field(default=True, description="Whether the operation completed successfully")
    error: Optional[str] = Field(default=None, description="Failure description if unsuccessful")

    model_config = {"arbitrary_types_allowed": True}


__all__ = [
    "CodingOperation",
    "DiagnosticSeverity",
    "Diagnostic",
    "FileArtifact",
    "ExecutionConfig",
    "ExecutionOutput",
    "TestStatus",
    "TestCaseResult",
    "TestSummary",
    "VerificationStatus",
    "VerificationResult",
    "CodeAnalysisReport",
    "CodingInput",
    "CodingResult",
]
