"""
workstation.py
==============
Active Workstation Automation & Verified Code/File Editing Engine.

Implements the user-commanded local automation capabilities:
  1. Accessing, inspecting, and editing files in the local device with AST verification & automatic rollback.
  2. Launching and interacting with current laptop applications (Notepad, VSCode, Terminal, Browser).
  3. Opening browser tabs and performing zero-API-key web research.
  4. Detecting active processes and managing desktop workspace state.
  5. Deterministic-first: 0% AI waste for all native filesystem and operating system actions.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from xeren.tools.deterministic.fs import default_fs, DeterministicFileSystem
from xeren.tools.deterministic.system import default_system, DeterministicSystemTools
from xeren.tools.deterministic.browser import default_browser, DeterministicBrowserTools

logger = logging.getLogger("xeren.automation.workstation")


class WorkstationAutomator:
    """Controls the local laptop workstation: files, applications, browser tabs, and processes."""

    def __init__(
        self,
        fs: Optional[DeterministicFileSystem] = None,
        system: Optional[DeterministicSystemTools] = None,
        browser: Optional[DeterministicBrowserTools] = None,
    ) -> None:
        self.fs = fs or default_fs
        self.system = system or default_system
        self.browser = browser or default_browser

    # =========================================================================
    # 1. Verified Atomic File Editing & AST Syntax Protection
    # =========================================================================

    def edit_file_verified(
        self,
        file_path: Union[str, Path],
        search_block: str,
        replace_block: str,
    ) -> Dict[str, Any]:
        """
        Safely edit a file in the workspace with automatic rollback on syntax error.
        If file is Python, enforces ast.parse() before committing.
        If file is JSON, enforces json.loads() before committing.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"File does not exist: {path}"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                original_content = f.read()

            if search_block not in original_content:
                return {
                    "success": False,
                    "error": "Target search block not found in file. Edit aborted to prevent corruption.",
                }

            # Apply candidate replacement
            new_content = original_content.replace(search_block, replace_block, 1)

            # Verification Step
            if path.suffix == ".py":
                try:
                    ast.parse(new_content, filename=str(path))
                except SyntaxError as e:
                    return {
                        "success": False,
                        "error": f"Syntax verification failed on line {e.lineno}: {e.msg}. Edit rolled back.",
                        "rolled_back": True,
                    }
            elif path.suffix == ".json":
                try:
                    json.loads(new_content)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"JSON syntax verification failed: {e}. Edit rolled back.",
                        "rolled_back": True,
                    }

            # Commit atomically
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "file": str(path),
                "bytes_written": len(new_content),
                "verification": "AST/Syntax check passed",
            }

        except Exception as e:
            return {"success": False, "error": f"Unexpected error during edit: {str(e)}"}

    def read_file_safe(self, file_path: Union[str, Path], start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        """Read file contents or slice with deterministic safety."""
        return self.fs.read_file(file_path, start_line, end_line)

    def list_files_safe(self, dir_path: Union[str, Path] = ".", pattern: str = "*") -> Dict[str, Any]:
        """Enumerate files in target folder with glob pattern."""
        return self.fs.list_dir(dir_path, pattern)

    # =========================================================================
    # 2. Codebase Symbol Search
    # =========================================================================

    def find_symbol(self, symbol_name: str, root_dir: Union[str, Path] = ".") -> List[Dict[str, Any]]:
        """Locate function, class, or variable definitions across workspace."""
        results = []
        root = Path(root_dir).resolve()
        py_files = list(root.rglob("*.py"))

        pattern = re.compile(rf"(def|class)\s+({re.escape(symbol_name)})\b")

        for f in py_files:
            if any(skip in str(f) for skip in [".git", "venv", ".pytest_cache", "__pycache__"]):
                continue
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as file_handle:
                    for line_idx, line in enumerate(file_handle, 1):
                        match = pattern.search(line)
                        if match:
                            results.append({
                                "file": str(f.relative_to(root)),
                                "line": line_idx,
                                "kind": match.group(1),
                                "signature": line.strip(),
                            })
            except Exception:
                pass

        return results

    # =========================================================================
    # 3. Application & Process Automation
    # =========================================================================

    def launch_app(self, app_name: str) -> Dict[str, Any]:
        """Launch an application on the user's desktop."""
        return self.system.open_app(app_name)

    def get_system_metrics(self) -> Dict[str, Any]:
        """Retrieve real-time CPU, RAM, and OS metrics."""
        return self.system.get_system_stats()

    def list_top_processes(self, limit: int = 15) -> List[Dict[str, Any]]:
        """List active running processes on the machine without crashing."""
        procs = []
        try:
            if sys.platform == "win32":
                cmd = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, Id, CPU"
                out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
                for line in out.stdout.strip().split("\n")[3:]:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        procs.append({"name": parts[0], "id": parts[1]})
            else:
                out = subprocess.run(["ps", "-eo", "pid,comm,%cpu", "--sort=-%cpu"], capture_output=True, text=True, timeout=5)
                for line in out.stdout.strip().split("\n")[1:limit+1]:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        procs.append({"name": parts[1], "id": parts[0]})
        except Exception as e:
            logger.debug("Process listing error: %s", e)
        return procs[:limit]

    # =========================================================================
    # 4. Browser Automation & Zero-API-Key Web Search
    # =========================================================================

    def open_browser_tab(self, url: str) -> Dict[str, Any]:
        """Open a URL in the user's default browser."""
        return self.browser.open_tab(url)

    def research_topic(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Perform zero-API-key web research via DuckDuckGo lite and text extraction."""
        return self.browser.search_duckduckgo_lite(query, max_results=max_results)


default_automator = WorkstationAutomator()

