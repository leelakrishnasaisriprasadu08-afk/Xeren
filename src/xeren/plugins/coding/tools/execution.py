"""Controlled execution sandbox and security boundary for safe code execution."""

from abc import ABC, abstractmethod
import asyncio
from contextlib import contextmanager
import logging
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Dict, Generator, List, Optional, Sequence, Union

from xeren.plugins.coding.schemas import ExecutionConfig, ExecutionOutput, FileArtifact

logger = logging.getLogger("xeren.plugins.coding.tools.execution")

# Blocked shells and dangerous utilities
BLOCKED_COMMANDS = frozenset([
    "sh", "bash", "zsh", "csh", "ksh", "fish",
    "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe",
    "rm", "del", "erase", "curl", "wget", "nc", "netcat", "ncat",
    "sudo", "su", "chmod", "chown", "dd", "mkfs", "format",
])

# Whitelisted safe environment variable names
SAFE_ENV_VARS = frozenset([
    "PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR",
    "TEMP", "TMP", "PYTHONPATH", "PYTHONHOME",
    "LANG", "LC_ALL", "TZ", "COMSPEC",
])

# Regex patterns for secret/credential redaction
SECRET_PATTERNS = [
    # Authorization / Bearer tokens
    (re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*"), r"\1[REDACTED_TOKEN]"),
    # OpenAI / Anthropic / GitHub / AWS keys
    (re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9\-]+)\b"), "[REDACTED_API_KEY]"),
    # Generic key-value credentials: password="xxx", api_key="xxx", secret="xxx"
    (re.compile(r"""(?i)(password|secret|token|api_key|auth_token)\s*[:=]\s*['"][^'"]+['"]"""), r"\1='[REDACTED]'"),
]


class SecurityViolationError(Exception):
    """Raised when an execution request violates sandbox security policies."""
    pass


def redact_secrets(text: str) -> str:
    """Sanitize and mask sensitive credentials and API keys in text output."""
    if not text:
        return text
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class BaseCodeExecutor(ABC):
    """Abstract base class for replaceable code execution backends."""

    @abstractmethod
    def execute(
        self,
        command: Sequence[str],
        working_dir: Path,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionOutput:
        """Synchronously execute a command within the sandboxed environment."""
        pass

    async def aexecute(
        self,
        command: Sequence[str],
        working_dir: Path,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionOutput:
        """Asynchronously execute a command within the sandboxed environment."""
        return await asyncio.to_thread(self.execute, command, working_dir, config)


class SubprocessSandboxExecutor(BaseCodeExecutor):
    """Secure local subprocess execution engine enforcing strict sandbox boundaries."""

    def __init__(self, default_config: Optional[ExecutionConfig] = None) -> None:
        self.default_config = default_config or ExecutionConfig()

    @staticmethod
    def is_safe_path(target_path: Union[str, Path], base_dir: Path) -> bool:
        """Check if target_path resolves strictly within base_dir without traversal."""
        try:
            resolved_base = base_dir.resolve()
            resolved_target = (base_dir / target_path).resolve()
            resolved_target.relative_to(resolved_base)
            return True
        except (ValueError, RuntimeError):
            return False

    def validate_command(self, command: Sequence[str], allowed_commands: Sequence[str]) -> str:
        """Validate command against allowlist and blocklist policies."""
        if not command:
            raise SecurityViolationError("Execution command cannot be empty.")

        raw_cmd = command[0].strip()
        exe_name = Path(raw_cmd).name.lower()

        # Check for blocked shell or dangerous utilities
        if exe_name in BLOCKED_COMMANDS:
            raise SecurityViolationError(
                f"Execution rejected: '{exe_name}' is a blocked binary or shell."
            )

        # Normalize allowed commands (match executable base name)
        allowed_bases = {Path(c).name.lower() for c in allowed_commands}
        # Also allow python version variants (e.g. python3, python3.12)
        if "python" in allowed_bases:
            allowed_bases.update(["python", "python3", "python.exe", "python3.exe"])
        if "pytest" in allowed_bases:
            allowed_bases.update(["pytest", "pytest.exe"])
        if "node" in allowed_bases:
            allowed_bases.update(["node", "node.exe"])

        if exe_name not in allowed_bases:
            raise SecurityViolationError(
                f"Execution rejected: '{exe_name}' is not in the allowed command policy {list(allowed_commands)}."
            )

        return raw_cmd

    def build_safe_environment(self, config: ExecutionConfig) -> Dict[str, str]:
        """Construct a minimal, restricted environment stripped of host secrets."""
        safe_env: Dict[str, str] = {}

        # 1. Inherit only strictly whitelisted system environment variables
        for var_name, var_val in os.environ.items():
            upper_name = var_name.upper()
            if upper_name in SAFE_ENV_VARS:
                # Disallow any var that mentions secrets even if in safe list
                if not any(k in upper_name for k in ("KEY", "SECRET", "TOKEN", "PASS")):
                    safe_env[var_name] = var_val

        # 2. Block network if network is disabled (default)
        if not config.network_enabled:
            safe_env["http_proxy"] = "http://127.0.0.1:0"
            safe_env["https_proxy"] = "http://127.0.0.1:0"
            safe_env["all_proxy"] = "http://127.0.0.1:0"
            safe_env["NO_PROXY"] = ""

        # 3. Add explicit non-sensitive custom environment variables
        for k, v in config.env_vars.items():
            upper_k = k.upper()
            if not any(s in upper_k for s in ("KEY", "SECRET", "TOKEN", "PASS")):
                safe_env[k] = v

        return safe_env

    @contextmanager
    def isolated_workspace(
        self,
        files: Optional[Sequence[FileArtifact]] = None,
        custom_dir: Optional[Union[str, Path]] = None,
    ) -> Generator[Path, None, None]:
        """Create and manage an isolated temporary directory for file writes and execution."""
        if custom_dir is not None:
            base_path = Path(custom_dir).resolve()
            base_path.mkdir(parents=True, exist_ok=True)
            if files:
                for f in files:
                    if not self.is_safe_path(f.file_path, base_path):
                        raise SecurityViolationError(
                            f"Path traversal detected: '{f.file_path}' attempts to escape workspace '{base_path}'"
                        )
                    target = (base_path / f.file_path).resolve()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(f.content, encoding="utf-8")
            yield base_path
        else:
            with tempfile.TemporaryDirectory(prefix="xeren_sandbox_") as tmp_dir:
                base_path = Path(tmp_dir).resolve()
                if files:
                    for f in files:
                        if not self.is_safe_path(f.file_path, base_path):
                            raise SecurityViolationError(
                                f"Path traversal detected: '{f.file_path}' attempts to escape workspace."
                            )
                        target = (base_path / f.file_path).resolve()
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(f.content, encoding="utf-8")
                yield base_path

    def execute(
        self,
        command: Sequence[str],
        working_dir: Path,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionOutput:
        """Execute command in sandbox with strict timeouts, size limits, and secret redaction."""
        cfg = config or self.default_config
        start_time = time.perf_counter()

        # Security check: validate command against allowlist
        self.validate_command(command, cfg.allowed_commands)

        # Build sanitized environment
        env = self.build_safe_environment(cfg)

        cmd_list = list(command)
        logger.debug("Executing sandboxed command: %s in %s", cmd_list, working_dir)

        try:
            process = subprocess.Popen(
                cmd_list,
                cwd=str(working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                env=env,
                shell=False,  # Critical security requirement
            )
        except Exception as err:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ExecutionOutput(
                exit_code=-1,
                error_message=f"Failed to start subprocess: {err}",
                duration_ms=duration_ms,
            )

        timed_out = False
        raw_stdout = b""
        raw_stderr = b""

        try:
            raw_stdout, raw_stderr = process.communicate(timeout=cfg.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            try:
                raw_stdout, raw_stderr = process.communicate(timeout=1.0)
            except Exception:
                pass
            logger.warning("Sandboxed execution timed out after %.2fs", cfg.timeout_seconds)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Decode output safely
        stdout_str = raw_stdout.decode("utf-8", errors="replace")
        stderr_str = raw_stderr.decode("utf-8", errors="replace")

        # Output-size truncation
        if len(stdout_str.encode("utf-8")) > cfg.max_output_bytes:
            stdout_str = stdout_str[: cfg.max_output_bytes] + "\n... [output truncated: exceeded max output bytes]"

        if len(stderr_str.encode("utf-8")) > cfg.max_output_bytes:
            stderr_str = stderr_str[: cfg.max_output_bytes] + "\n... [output truncated: exceeded max output bytes]"

        # Redact any credentials/tokens in output
        stdout_redacted = redact_secrets(stdout_str)
        stderr_redacted = redact_secrets(stderr_str)

        exit_code = process.returncode if not timed_out else -1

        return ExecutionOutput(
            exit_code=exit_code,
            stdout=stdout_redacted,
            stderr=stderr_redacted,
            timed_out=timed_out,
            duration_ms=duration_ms,
            error_message="Execution timed out" if timed_out else (None if exit_code == 0 else f"Process exited with code {exit_code}"),
        )


__all__ = [
    "SecurityViolationError",
    "redact_secrets",
    "BaseCodeExecutor",
    "SubprocessSandboxExecutor",
]
