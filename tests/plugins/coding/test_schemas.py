"""Tests for CodingPlugin schemas and input/output validation."""

import pytest
from pydantic import ValidationError

from xeren.plugins.coding.schemas import (
    CodingInput,
    CodingOperation,
    CodingResult,
    Diagnostic,
    DiagnosticSeverity,
    ExecutionConfig,
    ExecutionOutput,
    FileArtifact,
    TestSummary,
    VerificationResult,
    VerificationStatus,
)


def test_valid_coding_input_generate():
    """Verify valid CodingInput for generation."""
    inp = CodingInput(task="Write a binary search algorithm", language="python")
    assert inp.task == "Write a binary search algorithm"
    assert inp.operation == CodingOperation.GENERATE
    assert inp.language == "python"
    assert inp.execution_config.timeout_seconds == 10.0


def test_invalid_coding_input_generate_raises():
    """Verify empty task on generate raises ValidationError."""
    with pytest.raises(ValidationError):
        CodingInput(task="", operation=CodingOperation.GENERATE)


def test_valid_coding_input_analyze_and_syntax():
    """Verify valid inputs for analyze and syntax check."""
    inp = CodingInput(
        operation=CodingOperation.ANALYZE,
        source_code="def add(a, b): return a + b",
    )
    assert inp.operation == CodingOperation.ANALYZE
    assert inp.source_code is not None

    inp_syntax = CodingInput(
        operation=CodingOperation.SYNTAX_CHECK,
        source_code="x = 10",
    )
    assert inp_syntax.operation == CodingOperation.SYNTAX_CHECK


def test_invalid_coding_input_analyze_missing_code_raises():
    """Verify missing source code on analyze raises ValidationError."""
    with pytest.raises(ValidationError):
        CodingInput(operation=CodingOperation.ANALYZE)


def test_invalid_coding_input_execute_missing_code_raises():
    """Verify missing code on execute raises ValidationError."""
    with pytest.raises(ValidationError):
        CodingInput(operation=CodingOperation.EXECUTE)


def test_execution_config_boundaries():
    """Verify ExecutionConfig boundary constraints."""
    with pytest.raises(ValidationError):
        ExecutionConfig(timeout_seconds=0.0)

    with pytest.raises(ValidationError):
        ExecutionConfig(timeout_seconds=61.0)

    with pytest.raises(ValidationError):
        ExecutionConfig(max_output_bytes=500)


def test_coding_result_serialization():
    """Verify CodingResult serialization and structured attributes."""
    file_art = FileArtifact(file_path="math_utils.py", content="def square(x): return x * x")
    diag = Diagnostic(message="Unused variable", severity=DiagnosticSeverity.WARNING, line=1, column=0)
    exec_out = ExecutionOutput(exit_code=0, stdout="Result: 16\n", duration_ms=45.2)
    verify_res = VerificationResult(
        status=VerificationStatus.PASSED,
        syntax_ok=True,
        analysis_ok=True,
        tests_ok=True,
        summary="All checks passed",
    )

    result = CodingResult(
        operation=CodingOperation.GENERATE,
        task="Create square function",
        language="python",
        files=[file_art],
        diagnostics=[diag],
        syntax_valid=True,
        execution_output=exec_out,
        verification=verify_res,
        success=True,
    )

    assert result.operation == CodingOperation.GENERATE
    assert len(result.files) == 1
    assert result.files[0].file_path == "math_utils.py"
    assert len(result.diagnostics) == 1
    assert result.execution_output is not None
    assert result.execution_output.exit_code == 0
    assert result.verification is not None
    assert result.verification.status == VerificationStatus.PASSED

    # Test serialization
    dumped = result.model_dump()
    assert dumped["operation"] == "generate"
    assert dumped["files"][0]["file_path"] == "math_utils.py"
    assert dumped["success"] is True
