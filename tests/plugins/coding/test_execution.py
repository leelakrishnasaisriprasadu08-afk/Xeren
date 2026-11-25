"""Tests for SubprocessSandboxExecutor and security enforcement."""

import os
from pathlib import Path
import sys
import pytest

from xeren.plugins.coding.schemas import ExecutionConfig, FileArtifact
from xeren.plugins.coding.tools.execution import (
    SecurityViolationError,
    SubprocessSandboxExecutor,
    redact_secrets,
)


def test_safe_execution_success():
    """Verify safe Python execution inside sandbox."""
    executor = SubprocessSandboxExecutor()
    files = [
        FileArtifact(file_path="main.py", content="print('Sandbox execution successful!')")
    ]
    with executor.isolated_workspace(files=files) as workspace:
        cmd = [sys.executable, "main.py"]
        out = executor.execute(cmd, working_dir=workspace)
        assert out.exit_code == 0
        assert "Sandbox execution successful!" in out.stdout
        assert out.timed_out is False


def test_path_traversal_prevention():
    """Verify attempts to write files outside sandbox directory are blocked."""
    executor = SubprocessSandboxExecutor()
    # Attempting path traversal via '..'
    files = [
        FileArtifact(file_path="../escaped.py", content="print('escaped!')")
    ]
    with pytest.raises(SecurityViolationError) as exc_info:
        with executor.isolated_workspace(files=files):
            pass
    assert "Path traversal detected" in str(exc_info.value)


def test_blocked_command_rejection():
    """Verify blocked commands and shells are strictly rejected."""
    executor = SubprocessSandboxExecutor()
    blocked = ["bash", "sh", "cmd.exe", "powershell", "rm", "curl", "wget"]
    with executor.isolated_workspace() as workspace:
        for b in blocked:
            with pytest.raises(SecurityViolationError) as exc_info:
                executor.execute([b, "arg"], working_dir=workspace)
            assert "blocked binary or shell" in str(exc_info.value)


def test_unallowed_command_rejection():
    """Verify commands not in the allowlist are rejected."""
    executor = SubprocessSandboxExecutor()
    config = ExecutionConfig(allowed_commands=["python"])
    with executor.isolated_workspace() as workspace:
        with pytest.raises(SecurityViolationError) as exc_info:
            executor.execute(["git", "status"], working_dir=workspace, config=config)
        assert "not in the allowed command policy" in str(exc_info.value)


def test_timeout_enforcement():
    """Verify long-running processes are cleanly killed on timeout."""
    executor = SubprocessSandboxExecutor()
    files = [
        FileArtifact(
            file_path="sleep_script.py",
            content="import time\ntime.sleep(5)\nprint('done')",
        )
    ]
    config = ExecutionConfig(timeout_seconds=0.3)
    with executor.isolated_workspace(files=files) as workspace:
        cmd = [sys.executable, "sleep_script.py"]
        out = executor.execute(cmd, working_dir=workspace, config=config)
        assert out.timed_out is True
        assert out.exit_code == -1
        assert "timed out" in (out.error_message or "").lower()


def test_output_size_truncation():
    """Verify large stdout output is truncated at max_output_bytes."""
    executor = SubprocessSandboxExecutor()
    # Print 5000 characters
    files = [
        FileArtifact(
            file_path="large_output.py",
            content="print('A' * 5000)",
        )
    ]
    config = ExecutionConfig(max_output_bytes=1024)
    with executor.isolated_workspace(files=files) as workspace:
        cmd = [sys.executable, "large_output.py"]
        out = executor.execute(cmd, working_dir=workspace, config=config)
        assert out.exit_code == 0
        assert "output truncated" in out.stdout
        assert len(out.stdout) < 2000


def test_secret_redaction():
    """Verify sensitive tokens and passwords are redacted from execution output."""
    raw_text = (
        "Authorization: Bearer abc123456789xyz-secret\n"
        "Found API key: sk-abcdefghijklmnopqrstuvwxyz123456\n"
        "Database password='SuperSecretPassword123'"
    )
    redacted = redact_secrets(raw_text)
    assert "abc123456789xyz" not in redacted
    assert "[REDACTED_TOKEN]" in redacted
    assert "sk-abcdefgh" not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "SuperSecretPassword123" not in redacted


def test_environment_variable_sanitization(monkeypatch: pytest.MonkeyPatch):
    """Verify host secrets in os.environ are stripped from subprocess environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-live-secret-test-key-1234567")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "very_secret_aws_key")
    monkeypatch.setenv("DB_PASSWORD", "super_password")

    executor = SubprocessSandboxExecutor()
    config = ExecutionConfig(network_enabled=False)
    safe_env = executor.build_safe_environment(config)

    assert "OPENAI_API_KEY" not in safe_env
    assert "AWS_SECRET_ACCESS_KEY" not in safe_env
    assert "DB_PASSWORD" not in safe_env
    assert safe_env.get("http_proxy") == "http://127.0.0.1:0"
