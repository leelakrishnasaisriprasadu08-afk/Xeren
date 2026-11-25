"""Desktop Application Operator & OS Supervisor tool for Xeren Automation on Windows."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("xeren.automation.desktop")


class DesktopSecurityError(Exception):
    """Raised when an unsafe system command or prohibited action is attempted."""
    pass


class WindowsDesktopOperator:
    """Provides active application launching, window/process supervision, and safe shell execution."""

    # Block destructive or catastrophic system commands
    BLOCKED_PATTERNS = [
        re.compile(r"\brmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\?", re.I),
        re.compile(r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]\s+[cC]:\\?", re.I),
        re.compile(r"\bformat\s+[a-zA-Z]:", re.I),
        re.compile(r"\bRemove-Item\s+.*-Recurse\s+.*[cC]:\\", re.I),
        re.compile(r"\bStop-Computer\b|\bRestart-Computer\b|\bshutdown\s+/[sSrR]", re.I),
        re.compile(r"\bClear-Disk\b|\bInitialize-Disk\b", re.I),
    ]

    # Pre-registered well-known Windows applications
    KNOWN_APPS: Dict[str, List[str]] = {
        "notepad": ["notepad.exe"],
        "calc": ["calc.exe"],
        "calculator": ["calc.exe"],
        "code": ["code.cmd", "code.exe", "code"],
        "vscode": ["code.cmd", "code.exe", "code"],
        "chrome": ["chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
        "edge": ["msedge.exe"],
        "terminal": ["wt.exe"],
        "wt": ["wt.exe"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe"],
        "explorer": ["explorer.exe"],
        "paint": ["mspaint.exe"],
    }

    def __init__(self, default_timeout_seconds: float = 30.0) -> None:
        self.default_timeout_seconds = default_timeout_seconds

    def resolve_app_path(self, app_name: str) -> Optional[str]:
        """Resolve app name or alias to an executable path on Windows."""
        key = app_name.lower().strip()
        candidates = self.KNOWN_APPS.get(key, [app_name])

        for candidate in candidates:
            # Check direct executable in PATH
            found = shutil.which(candidate)
            if found:
                return found

            # Check direct file path
            cand_path = Path(candidate)
            if cand_path.is_file():
                return str(cand_path)

            # Check LocalAppData WindowsApps
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if local_app_data:
                win_apps_path = Path(local_app_data) / "Microsoft" / "WindowsApps" / candidate
                if win_apps_path.is_file():
                    return str(win_apps_path)

        # Fallback to key itself if it exists in PATH
        return shutil.which(app_name) or app_name

    def launch_app(
        self,
        app_name_or_path: str,
        args: Optional[List[str]] = None,
        detached: bool = True,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Launch an installed desktop application."""
        resolved = self.resolve_app_path(app_name_or_path)
        if not resolved:
            return {
                "success": False,
                "error": f"Could not find or resolve application '{app_name_or_path}' on system.",
            }

        cmd = [resolved] + (args or [])
        try:
            creationflags = 0
            if detached and os.name == "nt":
                # DETACHED_PROCESS or CREATE_NEW_PROCESS_GROUP
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

            proc = subprocess.Popen(
                cmd,
                cwd=cwd or os.getcwd(),
                stdout=subprocess.DEVNULL if detached else subprocess.PIPE,
                stderr=subprocess.DEVNULL if detached else subprocess.PIPE,
                creationflags=creationflags,
                shell=False,
            )

            return {
                "success": True,
                "app": app_name_or_path,
                "resolved_path": resolved,
                "pid": proc.pid,
                "message": f"Successfully launched '{app_name_or_path}' (PID: {proc.pid}).",
            }
        except Exception as e:
            logger.exception("Failed to launch application '%s': %s", app_name_or_path, e)
            return {
                "success": False,
                "error": f"Failed to launch application '{app_name_or_path}': {e}",
            }

    def execute_shell(
        self,
        command: str,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        shell_type: str = "powershell",
    ) -> Dict[str, Any]:
        """Execute a safe shell command via PowerShell or CMD with supervision and timeouts."""
        # Validate security boundaries
        for blocked in self.BLOCKED_PATTERNS:
            if blocked.search(command):
                raise DesktopSecurityError(f"Command execution blocked by safety policy: '{command}' contains destructive patterns.")

        timeout_sec = timeout or self.default_timeout_seconds
        start_time = time.perf_counter()

        if shell_type.lower() == "powershell":
            shell_cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
        else:
            shell_cmd = ["cmd.exe", "/c", command]

        try:
            result = subprocess.run(
                shell_cmd,
                cwd=cwd or os.getcwd(),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                errors="replace",
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "duration_ms": duration_ms,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_sec} seconds.",
                "duration_ms": duration_ms,
                "command": command,
            }
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "duration_ms": duration_ms,
                "command": command,
            }

    def list_running_apps(self, filter_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List currently running Windows processes / applications."""
        try:
            cmd = ["tasklist", "/FO", "CSV", "/NH"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace")
            if result.returncode != 0:
                return []

            apps = []
            for line in result.stdout.splitlines():
                parts = [p.strip(' "') for p in line.split('","')]
                if len(parts) >= 2:
                    image_name, pid_str = parts[0], parts[1]
                    if filter_name and filter_name.lower() not in image_name.lower():
                        continue
                    try:
                        pid = int(pid_str)
                    except ValueError:
                        pid = -1
                    apps.append({
                        "name": image_name,
                        "pid": pid,
                        "session": parts[2] if len(parts) > 2 else "",
                        "mem_usage": parts[4] if len(parts) > 4 else "",
                    })
            return apps
        except Exception as e:
            logger.warning("Failed to list running apps via tasklist: %s", e)
            return []

    def terminate_app(self, pid_or_name: Union[int, str], force: bool = False) -> Dict[str, Any]:
        """Terminate a running process by PID or image name."""
        cmd = ["taskkill"]
        if force:
            cmd.append("/F")

        if isinstance(pid_or_name, int):
            cmd.extend(["/PID", str(pid_or_name)])
        else:
            name = pid_or_name if pid_or_name.endswith(".exe") else f"{pid_or_name}.exe"
            cmd.extend(["/IM", name])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace")
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "target": pid_or_name,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "target": pid_or_name}


__all__ = ["WindowsDesktopOperator", "DesktopSecurityError"]
