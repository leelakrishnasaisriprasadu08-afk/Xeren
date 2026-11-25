"""Deterministic System, Terminal, and OS Execution Tools.

Enforces deterministic local desktop commands, process execution, and system control.
Captures stdout, stderr, exit codes, and resource metrics.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("xeren.tools.deterministic.system")


class DeterministicSystemTools:
    """Controls OS processes, commands, and app launching deterministically."""

    # Disallowed dangerous commands for accidental data loss prevention
    DANGEROUS_PATTERNS = [
        "format c:",
        ":(){ :|:& };:",
        "rmdir /s /q c:\\",
        "rm -rf /",
        "del /f /s /q c:\\",
        "drop database",
        "drop table",
    ]

    def __init__(self, default_timeout_seconds: float = 60.0) -> None:
        self.default_timeout = default_timeout_seconds
        self.is_windows = platform.system().lower() == "windows"

    def run_command(
        self,
        command: str,
        cwd: Optional[Union[str, Path]] = None,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Safely execute a shell command deterministically."""
        clean_cmd = command.strip()
        cmd_lower = clean_cmd.lower()

        # Safety boundary check
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in cmd_lower:
                return {
                    "success": False,
                    "error": f"Command blocked by safety boundary: contains destructive pattern '{pattern}'",
                    "command": clean_cmd,
                    "exit_code": -1,
                }

        effective_timeout = timeout or self.default_timeout
        effective_cwd = str(Path(cwd).resolve()) if cwd else os.getcwd()
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start = time.perf_counter()
        try:
            # On Windows use powershell or cmd, on Unix use bash/sh
            shell_cmd = clean_cmd
            proc = subprocess.run(
                shell_cmd,
                shell=True,
                cwd=effective_cwd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=merged_env,
            )
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

            return {
                "success": proc.returncode == 0,
                "command": clean_cmd,
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "latency_ms": elapsed_ms,
                "cwd": effective_cwd,
            }
        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": False,
                "error": f"Command timed out after {effective_timeout}s",
                "command": clean_cmd,
                "exit_code": -1,
                "latency_ms": elapsed_ms,
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": False,
                "error": str(e),
                "command": clean_cmd,
                "exit_code": -1,
                "latency_ms": elapsed_ms,
            }

    def open_app(self, app_name_or_path: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Launch or open an installed application on the laptop."""
        clean_name = app_name_or_path.strip()
        cmd_args = args or []

        try:
            if self.is_windows:
                # Use start command or direct path
                full_cmd = f'start "" "{clean_name}" ' + " ".join(f'"{a}"' for a in cmd_args)
                subprocess.Popen(full_cmd, shell=True)
            elif platform.system().lower() == "darwin":
                subprocess.Popen(["open", "-a", clean_name] + cmd_args)
            else:
                subprocess.Popen([clean_name] + cmd_args)

            return {
                "success": True,
                "message": f"Successfully launched {clean_name}",
                "app": clean_name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to launch app '{clean_name}': {e}",
                "app": clean_name,
            }

    def get_system_stats(self) -> Dict[str, Any]:
        """Retrieve local system platform and architecture info without heavy AI."""
        return {
            "success": True,
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cwd": os.getcwd(),
        }


# Singleton instance
default_system = DeterministicSystemTools()
