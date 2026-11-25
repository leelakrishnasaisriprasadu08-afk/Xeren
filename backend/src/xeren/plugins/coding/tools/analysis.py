"""Static code analysis and security inspection tool."""

import ast
import logging
from typing import Any, List

from xeren.plugins.coding.schemas import CodeAnalysisReport

logger = logging.getLogger("xeren.plugins.coding.tools.analysis")


class CodeAnalysisTool:
    """Performs structural AST metrics and security smell detection."""

    def analyze_python(self, code: str) -> CodeAnalysisReport:
        """Perform AST-based structural and security analysis on Python code."""
        lines = [line for line in code.splitlines() if line.strip()]
        loc = len(lines)

        functions_count = 0
        classes_count = 0
        imports: List[str] = []
        security_warnings: List[str] = []
        decision_points = 0

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return CodeAnalysisReport(
                lines_of_code=loc,
                security_warnings=["SyntaxError encountered during AST parsing"],
            )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions_count += 1
            elif isinstance(node, ast.ClassDef):
                classes_count += 1
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

            # Cyclomatic complexity decision points
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert)):
                decision_points += 1
            elif isinstance(node, ast.BoolOp):
                decision_points += max(1, len(node.values) - 1)

            # Security anti-pattern checks
            if isinstance(node, ast.Call):
                func = node.func
                # Check for direct calls to eval() or exec()
                if isinstance(func, ast.Name):
                    if func.id in ("eval", "exec"):
                        security_warnings.append(f"Dangerous builtin function call: '{func.id}()' at line {node.lineno}")
                # Check for os.system()
                elif isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name) and func.value.id == "os" and func.attr == "system":
                        security_warnings.append(f"Dangerous system execution: 'os.system()' at line {node.lineno}")
                    # Check for subprocess calls with shell=True
                    elif isinstance(func.value, ast.Name) and func.value.id == "subprocess":
                        for kw in node.keywords:
                            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                security_warnings.append(f"Dangerous shell execution: 'subprocess.{func.attr}(..., shell=True)' at line {node.lineno}")
                    # Check for pickle.loads()
                    elif isinstance(func.value, ast.Name) and func.value.id == "pickle" and func.attr in ("loads", "load"):
                        security_warnings.append(f"Insecure deserialization: 'pickle.{func.attr}()' at line {node.lineno}")

        complexity = 1.0 + float(decision_points)

        return CodeAnalysisReport(
            lines_of_code=loc,
            functions_count=functions_count,
            classes_count=classes_count,
            imports=sorted(list(set(imports))),
            complexity_score=round(complexity, 2),
            security_warnings=security_warnings,
        )

    def analyze_generic(self, code: str) -> CodeAnalysisReport:
        """Fallback lightweight line analysis for non-Python languages."""
        lines = [line for line in code.splitlines() if line.strip()]
        security_warnings: List[str] = []

        # Generic smell keywords
        lower = code.lower()
        if "eval(" in lower:
            security_warnings.append("Potential dynamic evaluation: 'eval()' detected")
        if "system(" in lower or "exec(" in lower:
            security_warnings.append("Potential system command execution detected")

        return CodeAnalysisReport(
            lines_of_code=len(lines),
            functions_count=0,
            classes_count=0,
            imports=[],
            complexity_score=1.0,
            security_warnings=security_warnings,
        )

    def analyze(self, code: str, language: str = "python") -> CodeAnalysisReport:
        """Analyze code based on target language."""
        if language.lower().strip() == "python":
            return self.analyze_python(code)
        return self.analyze_generic(code)


__all__ = ["CodeAnalysisTool"]
