"""Diagnostics tool parsing tracebacks, runtime errors, and test failures."""

import logging
import re
from typing import List, Optional

from xeren.plugins.coding.schemas import Diagnostic, DiagnosticSeverity

logger = logging.getLogger("xeren.plugins.coding.tools.diagnostics")


class DiagnosticsTool:
    """Parses execution tracebacks, runtime exceptions, and generates actionable diagnostics."""

    TRACEBACK_LINE_RE = re.compile(r'File "([^"]+)", line (\d+)(?:, in (.+))?')
    EXCEPTION_RE = re.compile(r"^([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):\s*(.+)$", re.MULTILINE)

    def diagnose_traceback(self, stderr_text: str) -> List[Diagnostic]:
        """Extract structured diagnostics from Python traceback strings."""
        diagnostics: List[Diagnostic] = []
        if not stderr_text:
            return diagnostics

        # Find traceback file and line occurrences
        tb_matches = list(self.TRACEBACK_LINE_RE.finditer(stderr_text))
        exc_match = self.EXCEPTION_RE.search(stderr_text)

        error_type = exc_match.group(1) if exc_match else "RuntimeError"
        error_msg = exc_match.group(2) if exc_match else stderr_text.strip().splitlines()[-1] if stderr_text.strip() else "Unknown runtime failure"

        if tb_matches:
            # Take the innermost frame (last match in traceback)
            last_frame = tb_matches[-1]
            file_path = last_frame.group(1)
            line_no = int(last_frame.group(2))
        else:
            file_path = None
            line_no = None

        # Build actionable suggestions based on error type
        suggestion = self._suggest_fix(error_type, error_msg)
        full_message = f"{error_type}: {error_msg}"
        if suggestion:
            full_message = f"{full_message} | Suggestion: {suggestion}"

        diag = Diagnostic(
            message=full_message,
            severity=DiagnosticSeverity.ERROR,
            line=line_no,
            column=0,
            rule_id=f"python_{error_type.lower()}",
            file_path=file_path,
        )
        diagnostics.append(diag)
        return diagnostics

    def _suggest_fix(self, error_type: str, message: str) -> Optional[str]:
        """Provide rule-based diagnostic fix suggestions."""
        if error_type == "NameError":
            name_match = re.search(r"name '([^']+)' is not defined", message)
            if name_match:
                return f"Check if variable '{name_match.group(1)}' is spelled correctly or imported."
            return "Ensure all identifiers are defined or imported before usage."
        elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
            return "Verify module name or check if the dependency is installed in the environment."
        elif error_type == "TypeError":
            return "Verify parameter types, expected argument count, or callable types."
        elif error_type == "AttributeError":
            return "Verify the object type and inspect available methods and attributes."
        elif error_type == "IndexError":
            return "Verify list bounds and check length before indexing."
        elif error_type == "ZeroDivisionError":
            return "Guard division operations with a nonzero denominator check."
        elif error_type == "SyntaxError":
            return "Check line syntax, closing parentheses, quotes, or indentation."
        return None


__all__ = ["DiagnosticsTool"]
