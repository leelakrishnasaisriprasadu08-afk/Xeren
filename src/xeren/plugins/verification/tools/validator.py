"""Deterministic and structural validation tools for verification."""

import ast
import json
import re
from typing import Any, Dict, List, Optional

from xeren.plugins.verification.schemas import CheckResult, VerificationOperation


class StructuralValidatorTool:
    """Validates structural integrity, format requirements, syntax, and schema definitions."""

    def validate(
        self,
        candidate: Any,
        expected_format: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        operation: Optional[VerificationOperation] = None,
    ) -> List[CheckResult]:
        """Execute structural, format, schema, code, or data validation checks."""
        checks: List[CheckResult] = []

        # 1. Non-empty check
        empty_check = self._check_non_empty(candidate)
        checks.append(empty_check)
        if not empty_check.passed:
            return checks

        # 2. Format validation
        if expected_format:
            fmt_checks = self._check_format(candidate, expected_format.lower().strip())
            checks.extend(fmt_checks)

        # 3. Schema validation
        if schema_definition:
            schema_checks = self._check_schema(candidate, schema_definition)
            checks.extend(schema_checks)

        # 4. Modality-specific checks (Code / Data)
        if operation == VerificationOperation.CODE_VERIFICATION:
            checks.extend(self._check_code(candidate))
        elif operation == VerificationOperation.DATA_VERIFICATION:
            checks.extend(self._check_data(candidate))

        return checks

    def _check_non_empty(self, candidate: Any) -> CheckResult:
        if candidate is None:
            return CheckResult(
                name="null_check",
                passed=False,
                score=0.0,
                reason="Candidate output is None.",
                actionable_correction="Ensure the generator produces a non-null result.",
            )
        if isinstance(candidate, str) and not candidate.strip():
            return CheckResult(
                name="empty_string_check",
                passed=False,
                score=0.0,
                reason="Candidate output is an empty or whitespace-only string.",
                actionable_correction="Ensure the output contains meaningful content.",
            )
        if isinstance(candidate, (list, dict, set, tuple)) and len(candidate) == 0:
            return CheckResult(
                name="empty_collection_check",
                passed=False,
                score=0.0,
                reason="Candidate collection is empty.",
                actionable_correction="Ensure the output collection contains at least one item.",
            )
        return CheckResult(
            name="non_empty_check",
            passed=True,
            score=1.0,
            reason="Candidate output is populated.",
        )

    def _check_format(self, candidate: Any, fmt: str) -> List[CheckResult]:
        checks: List[CheckResult] = []
        if fmt == "json":
            if isinstance(candidate, (dict, list)):
                checks.append(
                    CheckResult(
                        name="json_format_check",
                        passed=True,
                        score=1.0,
                        reason="Candidate is already a structured JSON-compatible object.",
                    )
                )
            elif isinstance(candidate, str):
                try:
                    json.loads(candidate)
                    checks.append(
                        CheckResult(
                            name="json_format_check",
                            passed=True,
                            score=1.0,
                            reason="Candidate string successfully parsed as valid JSON.",
                        )
                    )
                except Exception as exc:
                    checks.append(
                        CheckResult(
                            name="json_format_check",
                            passed=False,
                            score=0.0,
                            reason=f"Invalid JSON string: {exc}",
                            actionable_correction="Format the output as valid JSON with double-quoted keys and strings.",
                        )
                    )
            else:
                checks.append(
                    CheckResult(
                        name="json_format_check",
                        passed=False,
                        score=0.0,
                        reason=f"Candidate type {type(candidate).__name__} cannot be parsed as JSON.",
                        actionable_correction="Provide a valid JSON string, dict, or list.",
                    )
                )

        elif fmt in ("python", "py"):
            text = candidate if isinstance(candidate, str) else str(candidate)
            # Strip markdown code fences if present
            code = self._strip_code_fence(text, "python")
            try:
                ast.parse(code)
                checks.append(
                    CheckResult(
                        name="python_syntax_check",
                        passed=True,
                        score=1.0,
                        reason="Python code parsed successfully without syntax errors.",
                    )
                )
            except SyntaxError as exc:
                checks.append(
                    CheckResult(
                        name="python_syntax_check",
                        passed=False,
                        score=0.0,
                        reason=f"Python syntax error on line {exc.lineno}: {exc.msg}",
                        actionable_correction=f"Fix syntax error near line {exc.lineno}: '{exc.text.strip() if exc.text else ''}'.",
                        details={"lineno": exc.lineno, "offset": exc.offset, "msg": exc.msg},
                    )
                )

        elif fmt == "markdown":
            text = candidate if isinstance(candidate, str) else str(candidate)
            has_md_structure = bool(
                re.search(r"^#+\s+|^\s*[-*+]\s+|^\s*\d+\.\s+|```|\[.*?\]\(.*?\)", text, re.MULTILINE)
            )
            checks.append(
                CheckResult(
                    name="markdown_format_check",
                    passed=has_md_structure or len(text.strip()) > 0,
                    score=1.0 if has_md_structure else 0.8,
                    reason="Markdown format detected." if has_md_structure else "Plain text accepted as basic markdown.",
                )
            )

        elif fmt == "sql":
            text = candidate if isinstance(candidate, str) else str(candidate)
            code = self._strip_code_fence(text, "sql")
            sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH"]
            has_keyword = any(kw in code.upper() for kw in sql_keywords)
            balanced_parens = code.count("(") == code.count(")")
            passed = has_keyword and balanced_parens
            checks.append(
                CheckResult(
                    name="sql_format_check",
                    passed=passed,
                    score=1.0 if passed else 0.0,
                    reason="SQL structure and balanced parentheses verified." if passed else "SQL keyword missing or unbalanced parentheses.",
                    actionable_correction="Ensure query starts with valid SQL command and has balanced parentheses." if not passed else None,
                )
            )
        return checks

    def _check_schema(self, candidate: Any, schema: Dict[str, Any]) -> List[CheckResult]:
        checks: List[CheckResult] = []
        obj = candidate
        if isinstance(candidate, str):
            try:
                obj = json.loads(candidate)
            except Exception:
                checks.append(
                    CheckResult(
                        name="schema_parsing_check",
                        passed=False,
                        score=0.0,
                        reason="Failed to parse candidate as JSON object for schema validation.",
                        actionable_correction="Ensure output is valid JSON before validating against schema.",
                    )
                )
                return checks

        expected_type = schema.get("type")
        if expected_type == "object":
            if not isinstance(obj, dict):
                checks.append(
                    CheckResult(
                        name="schema_type_check",
                        passed=False,
                        score=0.0,
                        reason=f"Expected JSON object (dict), got {type(obj).__name__}.",
                        actionable_correction="Wrap response in a JSON object.",
                    )
                )
                return checks

            # Required fields check
            required_fields = schema.get("required", [])
            missing = [f for f in required_fields if f not in obj]
            if missing:
                checks.append(
                    CheckResult(
                        name="schema_required_fields_check",
                        passed=False,
                        score=max(0.0, (len(required_fields) - len(missing)) / max(len(required_fields), 1)),
                        reason=f"Missing required fields in schema: {missing}",
                        actionable_correction=f"Include missing fields {missing} in the output.",
                        details={"missing_fields": missing},
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="schema_required_fields_check",
                        passed=True,
                        score=1.0,
                        reason="All required schema fields are present.",
                    )
                )

            # Property types check
            properties = schema.get("properties", {})
            invalid_types = []
            for prop_name, prop_schema in properties.items():
                if prop_name in obj:
                    val = obj[prop_name]
                    prop_type = prop_schema.get("type")
                    if prop_type and not self._match_json_type(val, prop_type):
                        invalid_types.append((prop_name, prop_type, type(val).__name__))

            if invalid_types:
                checks.append(
                    CheckResult(
                        name="schema_property_types_check",
                        passed=False,
                        score=0.5,
                        reason=f"Property type mismatches: {invalid_types}",
                        actionable_correction=f"Ensure types match schema definitions: {invalid_types}",
                        details={"invalid_types": invalid_types},
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="schema_property_types_check",
                        passed=True,
                        score=1.0,
                        reason="All present properties conform to schema types.",
                    )
                )

        elif expected_type == "array":
            if not isinstance(obj, list):
                checks.append(
                    CheckResult(
                        name="schema_type_check",
                        passed=False,
                        score=0.0,
                        reason=f"Expected JSON array (list), got {type(obj).__name__}.",
                        actionable_correction="Wrap response in a JSON array.",
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="schema_type_check",
                        passed=True,
                        score=1.0,
                        reason=f"Candidate is a valid JSON array of length {len(obj)}.",
                    )
                )

        return checks

    def _check_code(self, candidate: Any) -> List[CheckResult]:
        checks: List[CheckResult] = []
        text = candidate if isinstance(candidate, str) else str(candidate)
        code = self._strip_code_fence(text, "python")
        try:
            tree = ast.parse(code)
            checks.append(
                CheckResult(
                    name="code_syntax_check",
                    passed=True,
                    score=1.0,
                    reason="Code parsed cleanly into valid Python AST.",
                )
            )
            # Check for empty body / dummy implementations
            functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            empty_funcs = []
            for fn in functions:
                if len(fn.body) == 1 and isinstance(fn.body[0], ast.Pass):
                    empty_funcs.append(fn.name)
            if empty_funcs:
                checks.append(
                    CheckResult(
                        name="code_completeness_check",
                        passed=False,
                        score=0.5,
                        reason=f"Functions contain only 'pass' stub implementations: {empty_funcs}",
                        actionable_correction=f"Implement actual logic for functions: {empty_funcs}",
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="code_completeness_check",
                        passed=True,
                        score=1.0,
                        reason="Code contains functional implementations without stub-only functions.",
                    )
                )
        except SyntaxError as exc:
            checks.append(
                CheckResult(
                    name="code_syntax_check",
                    passed=False,
                    score=0.0,
                    reason=f"Code syntax error on line {exc.lineno}: {exc.msg}",
                    actionable_correction=f"Fix syntax error near line {exc.lineno}: '{exc.text.strip() if exc.text else ''}'.",
                )
            )
        return checks

    def _check_data(self, candidate: Any) -> List[CheckResult]:
        checks: List[CheckResult] = []
        if isinstance(candidate, list):
            if len(candidate) == 0:
                checks.append(
                    CheckResult(
                        name="data_row_count_check",
                        passed=False,
                        score=0.0,
                        reason="Dataset contains 0 rows.",
                        actionable_correction="Provide at least 1 record in dataset.",
                    )
                )
                return checks

            if all(isinstance(row, dict) for row in candidate):
                keys_first = set(candidate[0].keys())
                inconsistent_rows = []
                for i, row in enumerate(candidate):
                    if set(row.keys()) != keys_first:
                        inconsistent_rows.append(i)
                if inconsistent_rows:
                    checks.append(
                        CheckResult(
                            name="data_schema_uniformity_check",
                            passed=False,
                            score=max(0.0, 1.0 - len(inconsistent_rows) / len(candidate)),
                            reason=f"Inconsistent column keys in rows: {inconsistent_rows[:5]}",
                            actionable_correction="Ensure all data records have identical schema columns.",
                        )
                    )
                else:
                    checks.append(
                        CheckResult(
                            name="data_schema_uniformity_check",
                            passed=True,
                            score=1.0,
                            reason=f"All {len(candidate)} rows share uniform schema keys: {sorted(keys_first)}",
                        )
                    )
            else:
                checks.append(
                    CheckResult(
                        name="data_row_type_check",
                        passed=True,
                        score=0.8,
                        reason=f"Dataset contains {len(candidate)} non-dictionary elements.",
                    )
                )
        elif isinstance(candidate, dict):
            checks.append(
                CheckResult(
                    name="data_dict_check",
                    passed=True,
                    score=1.0,
                    reason=f"Dataset is a valid key-value mapping with {len(candidate)} top-level fields.",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="data_type_check",
                    passed=False,
                    score=0.0,
                    reason=f"Unsupported data representation type: {type(candidate).__name__}",
                    actionable_correction="Provide structured data as a list of record dicts or a dictionary.",
                )
            )
        return checks

    def _strip_code_fence(self, text: str, lang: str = "") -> str:
        pattern = rf"^```(?:{lang})?\s*\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        # Check generic triple backticks
        match_generic = re.search(r"^```\w*\s*\n(.*?)\n```", text, re.DOTALL)
        if match_generic:
            return match_generic.group(1)
        return text

    def _match_json_type(self, val: Any, json_type: str) -> bool:
        if json_type == "string":
            return isinstance(val, str)
        if json_type == "number":
            return isinstance(val, (int, float)) and not isinstance(val, bool)
        if json_type == "integer":
            return isinstance(val, int) and not isinstance(val, bool)
        if json_type == "boolean":
            return isinstance(val, bool)
        if json_type == "array":
            return isinstance(val, (list, tuple))
        if json_type == "object":
            return isinstance(val, dict)
        if json_type == "null":
            return val is None
        return True
