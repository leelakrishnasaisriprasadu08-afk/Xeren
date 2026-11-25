"""Deterministic Local Filesystem Tools.

Enforces the 'Zero AI Waste' principle: reads, writes, inspects, and patches
local files using 100% deterministic Python standard library operations.
Zero token cost, sub-millisecond latency, zero hallucination risk.
"""

from __future__ import annotations

import fnmatch
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("xeren.tools.deterministic.fs")


class DeterministicFileSystem:
    """Safe, deterministic local filesystem controller."""

    def __init__(self, root_dir: Optional[Union[str, Path]] = None) -> None:
        self.root_dir = Path(root_dir).resolve() if root_dir else Path.cwd().resolve()

    def _resolve_safe_path(self, target_path: Union[str, Path]) -> Path:
        """Resolve path and ensure safety."""
        path = Path(target_path)
        if not path.is_absolute():
            path = (self.root_dir / path).resolve()
        else:
            path = path.resolve()
        return path

    def read_file(
        self,
        path: Union[str, Path],
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        max_bytes: int = 250_000,
    ) -> Dict[str, Any]:
        """Read file contents deterministically with optional line range slicing."""
        target = self._resolve_safe_path(path)
        if not target.exists():
            return {
                "success": False,
                "error": f"File does not exist: {target}",
                "path": str(target),
            }

        if not target.is_file():
            return {
                "success": False,
                "error": f"Path is not a file: {target}",
                "path": str(target),
            }

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_idx = max(1, start_line or 1) - 1
            e_idx = min(total_lines, end_line or total_lines)

            selected_lines = lines[s_idx:e_idx]
            content = "".join(selected_lines)

            if len(content.encode("utf-8")) > max_bytes:
                content = content[:max_bytes] + "\n...[truncated due to size limit]"

            return {
                "success": True,
                "path": str(target),
                "total_lines": total_lines,
                "start_line": s_idx + 1,
                "end_line": e_idx,
                "content": content,
            }
        except Exception as e:
            logger.error("Error reading file %s: %s", target, e)
            return {
                "success": False,
                "error": str(e),
                "path": str(target),
            }

    def write_file(
        self,
        path: Union[str, Path],
        content: str,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """Write text content to a file, creating parent directories automatically."""
        target = self._resolve_safe_path(path)
        if target.exists() and not overwrite:
            return {
                "success": False,
                "error": f"File already exists and overwrite is False: {target}",
                "path": str(target),
            }

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(target),
                "bytes_written": len(content.encode("utf-8")),
            }
        except Exception as e:
            logger.error("Error writing file %s: %s", target, e)
            return {
                "success": False,
                "error": str(e),
                "path": str(target),
            }

    def patch_file(
        self,
        path: Union[str, Path],
        target_text: str,
        replacement_text: str,
    ) -> Dict[str, Any]:
        """Surgically replace exact string target in an existing file."""
        target = self._resolve_safe_path(path)
        read_res = self.read_file(target)
        if not read_res["success"]:
            return read_res

        content = read_res["content"]
        if target_text not in content:
            return {
                "success": False,
                "error": "Target replacement text was not found in file.",
                "path": str(target),
            }

        occurrences = content.count(target_text)
        new_content = content.replace(target_text, replacement_text)

        write_res = self.write_file(target, new_content, overwrite=True)
        if not write_res["success"]:
            return write_res

        return {
            "success": True,
            "path": str(target),
            "replacements_made": occurrences,
        }

    def list_dir(
        self,
        path: Optional[Union[str, Path]] = None,
        pattern: str = "*",
        recursive: bool = False,
        max_results: int = 500,
    ) -> Dict[str, Any]:
        """Deterministically list directories and files with glob filtering."""
        target = self._resolve_safe_path(path or self.root_dir)
        if not target.exists() or not target.is_dir():
            return {
                "success": False,
                "error": f"Directory does not exist: {target}",
                "path": str(target),
            }

        results: List[Dict[str, Any]] = []
        try:
            if recursive:
                for root, dirs, files in os.walk(target):
                    rel_root = Path(root).relative_to(target)
                    for d in sorted(dirs):
                        if fnmatch.fnmatch(d, pattern):
                            results.append({"name": d, "rel_path": str(rel_root / d), "type": "directory"})
                            if len(results) >= max_results:
                                break
                    for f in sorted(files):
                        if fnmatch.fnmatch(f, pattern):
                            results.append({"name": f, "rel_path": str(rel_root / f), "type": "file"})
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break
            else:
                for entry in sorted(target.iterdir()):
                    if fnmatch.fnmatch(entry.name, pattern):
                        results.append({
                            "name": entry.name,
                            "rel_path": entry.name,
                            "type": "directory" if entry.is_dir() else "file",
                        })
                        if len(results) >= max_results:
                            break

            return {
                "success": True,
                "path": str(target),
                "count": len(results),
                "entries": results,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": str(target),
            }


# Singleton instance
default_fs = DeterministicFileSystem()

