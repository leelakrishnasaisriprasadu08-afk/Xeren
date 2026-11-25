"""Tests for StructuralValidatorTool (null/empty checks, formats, syntax, schema, code, data)."""

import pytest

from xeren.plugins.verification.schemas import VerificationOperation
from xeren.plugins.verification.tools.validator import StructuralValidatorTool


@pytest.fixture
def validator():
    return StructuralValidatorTool()


def test_validator_null_candidate(validator):
    """Verify null candidate produces failed CheckResult with actionable correction."""
    checks = validator.validate(candidate=None)
    assert len(checks) == 1
    assert checks[0].name == "null_check"
    assert checks[0].passed is False
    assert checks[0].score == 0.0
    assert "None" in str(checks[0].reason)
    assert checks[0].actionable_correction is not None


def test_validator_empty_string(validator):
    """Verify empty or whitespace string produces failed CheckResult."""
    checks = validator.validate(candidate="   \n\t  ")
    assert len(checks) == 1
    assert checks[0].name == "empty_string_check"
    assert checks[0].passed is False
    assert checks[0].score == 0.0


def test_validator_empty_collection(validator):
    """Verify empty list or dict produces failed CheckResult."""
    checks_list = validator.validate(candidate=[])
    assert checks_list[0].name == "empty_collection_check"
    assert checks_list[0].passed is False

    checks_dict = validator.validate(candidate={})
    assert checks_dict[0].name == "empty_collection_check"
    assert checks_dict[0].passed is False


def test_validator_json_format(validator):
    """Verify JSON format validation handles valid and invalid strings."""
    # Valid dict directly
    checks = validator.validate(candidate={"key": "val"}, expected_format="json")
    json_check = next(c for c in checks if c.name == "json_format_check")
    assert json_check.passed is True
    assert json_check.score == 1.0

    # Valid string
    checks_str = validator.validate(candidate='{"status": "ok", "code": 200}', expected_format="json")
    json_check_str = next(c for c in checks_str if c.name == "json_format_check")
    assert json_check_str.passed is True

    # Malformed JSON string
    checks_bad = validator.validate(candidate='{unquoted_key: 123,}', expected_format="json")
    bad_check = next(c for c in checks_bad if c.name == "json_format_check")
    assert bad_check.passed is False
    assert bad_check.score == 0.0
    assert bad_check.actionable_correction is not None


def test_validator_python_syntax(validator):
    """Verify Python syntax validation parses valid AST and pinpoints syntax errors."""
    valid_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    checks = validator.validate(candidate=valid_code, expected_format="python")
    py_check = next(c for c in checks if c.name == "python_syntax_check")
    assert py_check.passed is True

    # Code inside markdown code fence
    fence_code = f"```python\n{valid_code}\n```"
    checks_fence = validator.validate(candidate=fence_code, expected_format="python")
    py_fence_check = next(c for c in checks_fence if c.name == "python_syntax_check")
    assert py_fence_check.passed is True

    # Syntax error
    invalid_code = "def broken(:\n    pass"
    checks_err = validator.validate(candidate=invalid_code, expected_format="python")
    err_check = next(c for c in checks_err if c.name == "python_syntax_check")
    assert err_check.passed is False
    assert err_check.score == 0.0
    assert err_check.details.get("lineno") is not None
    assert err_check.actionable_correction is not None


def test_validator_sql_format(validator):
    """Verify SQL format validation checks commands and balanced parentheses."""
    valid_sql = "SELECT id, name FROM users WHERE active = 1 AND (age > 18 OR role = 'admin');"
    checks = validator.validate(candidate=valid_sql, expected_format="sql")
    sql_check = next(c for c in checks if c.name == "sql_format_check")
    assert sql_check.passed is True

    # Unbalanced parentheses
    unbalanced_sql = "SELECT id FROM users WHERE (age > 18"
    checks_unbal = validator.validate(candidate=unbalanced_sql, expected_format="sql")
    unbal_check = next(c for c in checks_unbal if c.name == "sql_format_check")
    assert unbal_check.passed is False


def test_validator_schema_definition(validator):
    """Verify schema definition checks required properties and types."""
    schema = {
        "type": "object",
        "required": ["name", "age", "is_admin"],
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "is_admin": {"type": "boolean"},
        },
    }

    # Valid candidate
    good_cand = {"name": "Alice", "age": 30, "is_admin": True}
    checks_good = validator.validate(candidate=good_cand, schema_definition=schema)
    req_check = next(c for c in checks_good if c.name == "schema_required_fields_check")
    assert req_check.passed is True

    # Missing required field
    bad_cand = {"name": "Bob"}
    checks_bad = validator.validate(candidate=bad_cand, schema_definition=schema)
    req_bad = next(c for c in checks_bad if c.name == "schema_required_fields_check")
    assert req_bad.passed is False
    assert "missing" in str(req_bad.reason).lower()
    assert req_bad.actionable_correction is not None

    # Property type mismatch
    type_bad_cand = {"name": "Charlie", "age": "thirty", "is_admin": "yes"}
    checks_types = validator.validate(candidate=type_bad_cand, schema_definition=schema)
    type_check = next(c for c in checks_types if c.name == "schema_property_types_check")
    assert type_check.passed is False
    assert type_check.details.get("invalid_types") is not None


def test_validator_code_verification_stubs(validator):
    """Verify CODE_VERIFICATION detects empty stub functions with pass."""
    stub_code = "def compute_result(x: int):\n    pass\n"
    checks = validator.validate(candidate=stub_code, operation=VerificationOperation.CODE_VERIFICATION)
    complete_check = next(c for c in checks if c.name == "code_completeness_check")
    assert complete_check.passed is False
    assert "compute_result" in str(complete_check.reason)
    assert complete_check.actionable_correction is not None


def test_validator_data_verification_uniformity(validator):
    """Verify DATA_VERIFICATION identifies mismatched column keys across records."""
    uniform_data = [
        {"id": 1, "name": "Alpha"},
        {"id": 2, "name": "Beta"},
    ]
    checks_uniform = validator.validate(candidate=uniform_data, operation=VerificationOperation.DATA_VERIFICATION)
    uni_check = next(c for c in checks_uniform if c.name == "data_schema_uniformity_check")
    assert uni_check.passed is True

    mismatched_data = [
        {"id": 1, "name": "Alpha"},
        {"id": 2, "wrong_key": "Beta"},
    ]
    checks_mismatch = validator.validate(candidate=mismatched_data, operation=VerificationOperation.DATA_VERIFICATION)
    mis_check = next(c for c in checks_mismatch if c.name == "data_schema_uniformity_check")
    assert mis_check.passed is False
    assert mis_check.actionable_correction is not None
