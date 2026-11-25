"""Tests for Website Plugin schemas and data models."""

import pytest
from pydantic import ValidationError

from xeren.plugins.coding.schemas import Diagnostic, DiagnosticSeverity, FileArtifact
from xeren.plugins.website.schemas import (
    PreviewInfo,
    SecurityFinding,
    SecurityFindingSeverity,
    SecurityReport,
    ValidationResult,
    WebsiteInput,
    WebsiteOperation,
    WebsiteResult,
    WebsiteSpecification,
    WebsiteType,
)


def test_website_specification_defaults():
    """Verify WebsiteSpecification defaults and attributes."""
    spec = WebsiteSpecification(
        site_purpose="Build an AI startup landing page",
        target_audience="Developers and investors",
        pages=["index.html", "about.html"],
        sections=["Hero", "Features", "Pricing"],
        features=["Newsletter signup", "Dark mode"],
    )
    assert spec.site_purpose == "Build an AI startup landing page"
    assert len(spec.pages) == 2
    assert spec.technology_choice == "html/css/js"
    assert len(spec.sections) == 3


def test_validation_result_model():
    """Verify ValidationResult model structure and diagnostics aggregation."""
    diag = Diagnostic(
        message="Unclosed tag",
        severity=DiagnosticSeverity.ERROR,
        rule_id="html_unclosed",
        file_path="index.html",
        line=12,
    )
    val_res = ValidationResult(
        is_valid=False,
        html_ok=False,
        diagnostics=[diag],
        details={"error_count": 1},
    )
    assert val_res.is_valid is False
    assert val_res.html_ok is False
    assert val_res.css_ok is True
    assert len(val_res.diagnostics) == 1
    assert val_res.diagnostics[0].rule_id == "html_unclosed"


def test_security_models():
    """Verify SecurityFinding and SecurityReport models."""
    finding = SecurityFinding(
        rule_id="SEC_INLINE_KEY",
        severity=SecurityFindingSeverity.CRITICAL,
        message="API key detected",
        file_path="script.js",
        line=15,
        snippet="const key = 'sk-12345';",
    )
    report = SecurityReport(
        passed=False,
        findings=[finding],
        scanned_files_count=3,
        summary="1 critical issue found",
    )
    assert report.passed is False
    assert len(report.findings) == 1
    assert "Static Security Analysis" in report.audit_type
    assert report.findings[0].severity == SecurityFindingSeverity.CRITICAL


def test_preview_info_model():
    """Verify PreviewInfo structure."""
    preview = PreviewInfo(
        provider="mock",
        preview_url="http://localhost:8080/index.html",
        is_live=False,
        status="simulated",
        message="Mock preview mode",
    )
    assert preview.provider == "mock"
    assert preview.is_live is False
    assert preview.status == "simulated"


def test_website_input_valid():
    """Verify valid WebsiteInput construction."""
    inp = WebsiteInput(
        requirement="Create a portfolio site",
        operation=WebsiteOperation.GENERATE,
        website_type=WebsiteType.PORTFOLIO,
        pages=["index.html"],
    )
    assert inp.operation == WebsiteOperation.GENERATE
    assert inp.website_type == WebsiteType.PORTFOLIO
    assert inp.requirement == "Create a portfolio site"


def test_website_input_generate_requires_requirement_or_spec():
    """Verify WebsiteInput fails validation if GENERATE has neither requirement nor spec."""
    with pytest.raises(ValidationError):
        WebsiteInput(
            requirement="",
            operation=WebsiteOperation.GENERATE,
            specification=None,
        )


def test_website_input_edit_requires_existing_files():
    """Verify WebsiteInput fails validation if EDIT has no existing files."""
    with pytest.raises(ValidationError):
        WebsiteInput(
            operation=WebsiteOperation.EDIT,
            modification_request="Change title to Hello",
            existing_files=[],
        )


def test_website_input_edit_requires_modification_or_requirement():
    """Verify WebsiteInput fails validation if EDIT has no instructions."""
    artifact = FileArtifact(file_path="index.html", content="<html></html>", language="html")
    with pytest.raises(ValidationError):
        WebsiteInput(
            operation=WebsiteOperation.EDIT,
            existing_files=[artifact],
            modification_request="",
            requirement="",
        )


def test_website_result_serialization():
    """Verify WebsiteResult serializes and deserializes accurately."""
    res = WebsiteResult(
        operation=WebsiteOperation.GENERATE,
        requirement="Modern landing page",
        website_type="landing_page",
        files=[FileArtifact(file_path="index.html", content="<html></html>", language="html")],
        detected_pages=["index.html"],
        success=True,
    )
    data = res.model_dump()
    assert data["operation"] == "generate"
    assert data["success"] is True
    assert len(data["files"]) == 1
    assert data["files"][0]["file_path"] == "index.html"

    reconstructed = WebsiteResult.model_validate(data)
    assert reconstructed.operation == WebsiteOperation.GENERATE
    assert len(reconstructed.files) == 1
