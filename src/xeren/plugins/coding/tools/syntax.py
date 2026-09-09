"""Syntax checking tool for multi-language and Python AST validation."""

import ast
import logging
from typing import List, Tuple

from xeren.plugins.coding.schemas import Diagnostic, DiagnosticSeverity

logger = logging.getLogger("xeren.plugins.coding.tools.syntax")


class SyntaxCheckTool:
    """Validates source code syntax and structural integrity."""

    def check_python_syntax(self, code: str, file_path: str = "main.py") -> Tuple[bool, List[Diagnostic]]:
        """Validate Python code using the standard library ast module."""
        diagnostics: List[Diagnostic] = []
        try:
            ast.parse(code, filename=file_path)
            return True, []
        except SyntaxError as err:
            diag = Diagnostic(
                message=str(err.msg or "Syntax error in Python code"),
                severity=DiagnosticSeverity.ERROR,
                line=err.lineno or 1,
                column=(err.offset or 1) - 1,
                rule_id="python_syntax_error",
                file_path=file_path,
            )
            diagnostics.append(diag)
            return False, diagnostics
        except Exception as err:
            diag = Diagnostic(
                message=f"Failed to parse syntax: {err}",
                severity=DiagnosticSeverity.ERROR,
                line=1,
                column=0,
                rule_id="parse_error",
                file_path=file_path,
            )
            diagnostics.append(diag)
            return False, diagnostics

    def check_bracket_balance(self, code: str, file_path: str = "code.txt") -> Tuple[bool, List[Diagnostic]]:
        """Check for balanced brackets, braces, and parentheses."""
        diagnostics: List[Diagnostic] = []
        stack: List[Tuple[str, int, int]] = []
        matching = {")": "(", "}": "{", "]": "["}

        lines = code.splitlines()
        in_single_quote = False
        in_double_quote = False

        for line_num, line in enumerate(lines, start=1):
            col = 0
            while col < len(line):
                char = line[col]

                # Basic string quote skipping (single line)
                if char == "'" and (col == 0 or line[col - 1] != "\\") and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif char == '"' and (col == 0 or line[col - 1] != "\\") and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif not in_single_quote and not in_double_quote:
                    if char in matching.values():
                        stack.append((char, line_num, col))
                    elif char in matching.keys():
                        expected = matching[char]
                        if not stack or stack[-1][0] != expected:
                            diag = Diagnostic(
                                message=f"Unmatched closing delimiter '{char}'",
                                severity=DiagnosticSeverity.ERROR,
                                line=line_num,
                                column=col,
                                rule_id="unmatched_delimiter",
                                file_path=file_path,
                            )
                            diagnostics.append(diag)
                            return False, diagnostics
                        stack.pop()
                col += 1

        if stack:
            unclosed_char, line_num, col = stack[-1]
            diag = Diagnostic(
                message=f"Unclosed opening delimiter '{unclosed_char}'",
                severity=DiagnosticSeverity.ERROR,
                line=line_num,
                column=col,
                rule_id="unclosed_delimiter",
                file_path=file_path,
            )
            diagnostics.append(diag)
            return False, diagnostics

        return True, []

    def check_syntax(self, code: str, language: str = "python", file_path: str = "main.py") -> Tuple[bool, List[Diagnostic]]:
        """Validate syntax based on specified language."""
        lang = language.lower().strip()
        if lang == "python":
            return self.check_python_syntax(code, file_path=file_path)
        # Fallback to structural bracket check for other languages
        return self.check_bracket_balance(code, file_path=file_path)


__all__ = ["SyntaxCheckTool"]
