"""Tests for WebsiteWorkflow end-to-end orchestration."""

import pytest

from xeren.plugins.coding.schemas import FileArtifact, VerificationStatus
from xeren.plugins.website.schemas import (
    WebsiteInput,
    WebsiteOperation,
    WebsiteResult,
    WebsiteType,
)
from xeren.plugins.website.workflow import WebsiteWorkflow


def _sample_valid_files():
    return [
        FileArtifact(
            file_path="index.html",
            content="<!DOCTYPE html><html lang='en'><head><title>Test</title><link rel='stylesheet' href='styles.css'></head><body><script src='script.js'></script></body></html>",
            language="html",
        ),
        FileArtifact(file_path="styles.css", content="body { margin: 0; }", language="css"),
        FileArtifact(file_path="script.js", content="console.log(1);", language="javascript"),
    ]


def test_workflow_generate():
    """Verify full generation flow: requirements -> generation -> validation -> security -> preview."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        requirement="Modern landing page for cloud analytics platform",
        operation=WebsiteOperation.GENERATE,
        website_type=WebsiteType.LANDING_PAGE,
    )

    res = workflow.run(inp)
    assert isinstance(res, WebsiteResult)
    assert res.operation == WebsiteOperation.GENERATE
    assert res.success is True
    assert len(res.files) >= 3
    assert res.specification is not None
    assert res.validation is not None
    assert res.validation.is_valid is True
    assert res.security_report is not None
    assert res.security_report.passed is True
    assert res.preview is not None
    assert res.verification_status == VerificationStatus.PASSED


def test_workflow_edit():
    """Verify workflow edit operation modifying existing files."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        operation=WebsiteOperation.EDIT,
        existing_files=_sample_valid_files(),
        modification_request="Update styles to dark theme",
    )

    res = workflow.run(inp)
    assert res.operation == WebsiteOperation.EDIT
    assert res.success is True
    assert len(res.modified_files) >= 1
    assert res.validation is not None
    assert res.validation.is_valid is True


def test_workflow_validate():
    """Verify workflow validate operation on existing files."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        operation=WebsiteOperation.VALIDATE,
        existing_files=_sample_valid_files(),
    )

    res = workflow.run(inp)
    assert res.operation == WebsiteOperation.VALIDATE
    assert res.success is True
    assert res.validation is not None
    assert res.validation.is_valid is True


def test_workflow_security_check():
    """Verify workflow security check operation."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        operation=WebsiteOperation.SECURITY_CHECK,
        existing_files=_sample_valid_files(),
    )

    res = workflow.run(inp)
    assert res.operation == WebsiteOperation.SECURITY_CHECK
    assert res.success is True
    assert res.security_report is not None
    assert res.security_report.passed is True


def test_workflow_verify():
    """Verify workflow verification combining validation and security."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        operation=WebsiteOperation.VERIFY,
        existing_files=_sample_valid_files(),
    )

    res = workflow.run(inp)
    assert res.operation == WebsiteOperation.VERIFY
    assert res.success is True
    assert res.verification_status == VerificationStatus.PASSED


def test_workflow_analyze_requirements():
    """Verify workflow analyze requirements operation."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        requirement="Create a mobile gaming portfolio",
        operation=WebsiteOperation.ANALYZE_REQUIREMENTS,
        website_type=WebsiteType.PORTFOLIO,
    )

    res = workflow.run(inp)
    assert res.operation == WebsiteOperation.ANALYZE_REQUIREMENTS
    assert res.success is True
    assert res.specification is not None
    assert "gaming portfolio" in res.specification.site_purpose.lower()


def test_workflow_preview():
    """Verify workflow preview operation."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        operation=WebsiteOperation.PREVIEW,
        existing_files=_sample_valid_files(),
    )

    res = workflow.run(inp)
    assert res.operation == WebsiteOperation.PREVIEW
    assert res.success is True
    assert res.preview is not None
    assert res.preview.preview_url is not None


@pytest.mark.asyncio
async def test_workflow_async_run():
    """Verify asynchronous workflow execution."""
    workflow = WebsiteWorkflow()
    inp = WebsiteInput(
        requirement="Personal finance dashboard",
        operation=WebsiteOperation.GENERATE,
        website_type=WebsiteType.DASHBOARD,
    )

    res = await workflow.arun(inp)
    assert res.operation == WebsiteOperation.GENERATE
    assert res.success is True
    assert len(res.files) >= 3


def test_workflow_detects_insecure_code_and_fails():
    """Verify workflow generation reports security failure when insecure code is present."""
    workflow = WebsiteWorkflow()
    insecure_files = [
        FileArtifact(
            file_path="index.html",
            content="<html><head></head><body><script>const key = 'sk-1234567890abcdef1234567890abcdef';</script></body></html>",
            language="html",
        )
    ]
    inp = WebsiteInput(
        operation=WebsiteOperation.SECURITY_CHECK,
        existing_files=insecure_files,
    )
    res = workflow.run(inp)
    assert res.success is False
    assert res.security_report is not None
    assert res.security_report.passed is False
