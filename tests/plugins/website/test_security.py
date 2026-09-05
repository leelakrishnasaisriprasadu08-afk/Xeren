"""Tests for WebsiteSecurityTool."""

import pytest

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.website.schemas import SecurityFindingSeverity
from xeren.plugins.website.tools.security import WebsiteSecurityTool


def _clean_project():
    return [
        FileArtifact(
            file_path="index.html",
            content="<!DOCTYPE html><html><head><title>Safe</title></head><body><h1>Safe Page</h1></body></html>",
            language="html",
        ),
        FileArtifact(
            file_path="script.js",
            content="document.addEventListener('DOMContentLoaded', () => { console.log('safe'); });",
            language="javascript",
        ),
    ]


def test_security_clean_project():
    """Verify clean project passes static security analysis."""
    scanner = WebsiteSecurityTool()
    report = scanner.check_security(_clean_project())

    assert report.passed is True
    assert len(report.findings) == 0
    assert "Static Security Analysis" in report.audit_type


def test_security_detects_openai_key():
    """Verify detection of inline OpenAI secret key."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="script.js",
            content="const apiKey = 'sk-1234567890abcdef1234567890abcdef';",
            language="javascript",
        )
    ]
    report = scanner.check_security(files)

    assert report.passed is False
    assert any(f.rule_id == "SEC_OPENAI_KEY" for f in report.findings)
    assert any(f.severity == SecurityFindingSeverity.CRITICAL for f in report.findings)


def test_security_detects_aws_key():
    """Verify detection of inline AWS credential key."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="script.js",
            content="const awsKey = 'AKIAIOSFODNN7EXAMPLE';",
            language="javascript",
        )
    ]
    report = scanner.check_security(files)

    assert report.passed is False
    assert any(f.rule_id == "SEC_AWS_KEY" for f in report.findings)


def test_security_detects_bearer_token():
    """Verify detection of inline Bearer authentication token."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="script.js",
            content="headers.append('Authorization', 'Bearer abcdef1234567890abcdef1234567890');",
            language="javascript",
        )
    ]
    report = scanner.check_security(files)

    assert report.passed is False
    assert any(f.rule_id == "SEC_BEARER_TOKEN" for f in report.findings)


def test_security_detects_unsafe_eval():
    """Verify detection of eval() in JavaScript."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="script.js",
            content="const res = eval(userInput);",
            language="javascript",
        )
    ]
    report = scanner.check_security(files)

    assert report.passed is False
    assert any(f.rule_id == "SEC_UNSAFE_EVAL" for f in report.findings)


def test_security_detects_unsafe_document_write():
    """Verify detection of document.write() in client script."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="script.js",
            content="document.write('<div>' + name + '</div>');",
            language="javascript",
        )
    ]
    report = scanner.check_security(files)

    assert report.passed is False
    assert any(f.rule_id == "SEC_UNSAFE_DOC_WRITE" for f in report.findings)


def test_security_detects_unsafe_innerhtml():
    """Verify detection of innerHTML assignment."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="script.js",
            content="element.innerHTML = '<span>' + data + '</span>';",
            language="javascript",
        )
    ]
    report = scanner.check_security(files)

    # innerHTML is MEDIUM severity (warning)
    assert any(f.rule_id == "SEC_UNSAFE_INNERHTML" for f in report.findings)


def test_security_detects_insecure_http_resource():
    """Verify detection of mixed content http:// resources."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="index.html",
            content="<script src='http://insecure-cdn.com/lib.js'></script>",
            language="html",
        )
    ]
    report = scanner.check_security(files)

    assert any(f.rule_id == "SEC_INSECURE_HTTP_RESOURCE" for f in report.findings)


def test_security_detects_suspicious_executable_download():
    """Verify detection of executable download links."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="index.html",
            content="<a href='payload.exe'>Download Update</a>",
            language="html",
        )
    ]
    report = scanner.check_security(files)

    assert report.passed is False
    assert any(f.rule_id == "SEC_SUSPICIOUS_EXECUTABLE" for f in report.findings)


def test_security_detects_path_traversal_in_link():
    """Verify detection of directory traversal sequence in href."""
    scanner = WebsiteSecurityTool()
    files = [
        FileArtifact(
            file_path="index.html",
            content="<a href='../../etc/shadow'>Confidential</a>",
            language="html",
        )
    ]
    report = scanner.check_security(files)

    assert report.passed is False
    assert any(f.rule_id == "SEC_PATH_TRAVERSAL_LINK" for f in report.findings)


@pytest.mark.asyncio
async def test_security_async():
    """Verify asynchronous security scan."""
    scanner = WebsiteSecurityTool()
    report = await scanner.acheck_security(_clean_project())
    assert report.passed is True
