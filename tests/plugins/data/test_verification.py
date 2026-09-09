"""Tests for DataVerificationTool and rule checking."""

import pytest

from xeren.plugins.data.schemas import (
    DataInput,
    DataOperation,
    DataValidationRule,
    StructuredDataset,
)
from xeren.plugins.data.tools.verification import DataVerificationTool


def test_verification_all_pass():
    """Verify data passing all validation rules."""
    records = [
        {"id": 1, "email": "a@xeren.ai", "age": 25, "role": "admin"},
        {"id": 2, "email": "b@xeren.ai", "age": 30, "role": "user"},
    ]
    dataset = StructuredDataset.from_records(records)
    tool = DataVerificationTool()

    rules = [
        DataValidationRule(rule_name="not_null", column="email"),
        DataValidationRule(rule_name="unique", column="id"),
        DataValidationRule(rule_name="value_range", column="age", parameters={"min_value": 18, "max_value": 65}),
        DataValidationRule(rule_name="allowed_values", column="role", parameters={"allowed": ["admin", "user"]}),
        DataValidationRule(rule_name="regex", column="email", parameters={"pattern": r"^[^@]+@[^@]+\.[^@]+$"}),
        DataValidationRule(rule_name="row_count", parameters={"min_rows": 1, "max_rows": 100}),
    ]

    inp = DataInput(
        operation=DataOperation.VERIFY,
        dataset=dataset,
        validation_rules=rules,
    )
    res = tool.execute(inp)
    assert res.success is True
    report = res.verification_report
    assert report is not None
    assert report.total_rules == 6
    assert report.passed_rules == 6
    assert report.failed_rules == 0
    assert report.is_valid is True
    assert report.quality_score == 1.0


def test_verification_findings_on_violations():
    """Verify data violating rules generates accurate findings and reduced quality score."""
    records = [
        {"id": 1, "email": "good@test.com", "age": 15},
        {"id": 1, "email": None, "age": 25},  # duplicate id, null email
    ]
    dataset = StructuredDataset.from_records(records)
    tool = DataVerificationTool()

    rules = [
        DataValidationRule(rule_name="unique", column="id"),
        DataValidationRule(rule_name="not_null", column="email"),
        DataValidationRule(rule_name="value_range", column="age", parameters={"min_value": 18}),
    ]

    inp = DataInput(
        operation=DataOperation.VERIFY,
        dataset=dataset,
        validation_rules=rules,
    )
    res = tool.execute(inp)
    assert res.success is True
    report = res.verification_report
    assert report is not None
    assert report.is_valid is False
    assert report.passed_rules == 0
    assert report.failed_rules == 3
    assert len(report.findings) == 3
    assert report.quality_score == 0.0

    # Ensure rule failures are logged in findings
    rule_names = {f.rule_name for f in report.findings}
    assert "unique" in rule_names
    assert "not_null" in rule_names
    assert "value_range" in rule_names
