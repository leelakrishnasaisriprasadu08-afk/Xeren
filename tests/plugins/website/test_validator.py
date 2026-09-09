"""Tests for WebsiteValidatorTool."""

import pytest

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.website.tools.validator import WebsiteValidatorTool


def _valid_project():
    return [
        FileArtifact(
            file_path="index.html",
            content=(
                "<!DOCTYPE html><html lang='en'>"
                "<head><title>Test</title><link rel='stylesheet' href='styles.css'></head>"
                "<body><header></header><main><p>Content</p></main><footer></footer><script src='script.js'></script></body>"
                "</html>"
            ),
            language="html",
        ),
        FileArtifact(
            file_path="styles.css",
            content="body { margin: 0; padding: 0; } /* clean comment */",
            language="css",
        ),
        FileArtifact(
            file_path="script.js",
            content="document.addEventListener('DOMContentLoaded', () => { console.log('ok'); });",
            language="javascript",
        ),
    ]


def test_validator_clean_project():
    """Verify clean website project passes all structural and syntax checks."""
    validator = WebsiteValidatorTool()
    res = validator.validate(_valid_project())

    assert res.is_valid is True
    assert res.structure_ok is True
    assert res.html_ok is True
    assert res.css_ok is True
    assert res.js_ok is True
    assert res.assets_ok is True
    assert len(res.diagnostics) == 0


def test_validator_missing_entrypoint():
    """Verify validator flags missing index.html."""
    validator = WebsiteValidatorTool()
    files = [
        FileArtifact(file_path="about.html", content="<html><head></head><body></body></html>", language="html"),
        FileArtifact(file_path="styles.css", content="body {}", language="css"),
    ]
    res = validator.validate(files)

    assert res.is_valid is False
    assert res.structure_ok is False
    assert any(d.rule_id == "web_missing_entrypoint" for d in res.diagnostics)


def test_validator_path_traversal():
    """Verify validator flags path traversal attempts in file names."""
    validator = WebsiteValidatorTool()
    files = [
        FileArtifact(file_path="index.html", content="<html><head></head><body></body></html>", language="html"),
        FileArtifact(file_path="../escape.txt", content="payload", language="text"),
    ]
    res = validator.validate(files)

    assert res.is_valid is False
    assert res.structure_ok is False
    assert any(d.rule_id == "web_path_traversal" for d in res.diagnostics)


def test_validator_malformed_html():
    """Verify validator flags missing head or body in HTML."""
    validator = WebsiteValidatorTool()
    files = [
        FileArtifact(
            file_path="index.html",
            content="<div>Only a div without html, head, or body tags</div>",
            language="html",
        )
    ]
    res = validator.validate(files)

    assert res.is_valid is False
    assert res.html_ok is False
    rule_ids = [d.rule_id for d in res.diagnostics]
    assert "html_missing_root" in rule_ids or "html_missing_head" in rule_ids


def test_validator_broken_asset_references():
    """Verify validator flags broken references to missing local files."""
    validator = WebsiteValidatorTool()
    files = [
        FileArtifact(
            file_path="index.html",
            content=(
                "<!DOCTYPE html><html><head><title>T</title>"
                "<link rel='stylesheet' href='missing_styles.css'>"
                "</head><body>"
                "<img src='missing_image.png'>"
                "<a href='missing_page.html'>Link</a>"
                "<script src='missing_script.js'></script>"
                "</body></html>"
            ),
            language="html",
        )
    ]
    res = validator.validate(files)

    assert res.is_valid is False
    assert res.assets_ok is False
    rule_ids = [d.rule_id for d in res.diagnostics]
    assert "asset_broken_stylesheet" in rule_ids
    assert "asset_broken_image" in rule_ids
    assert "asset_broken_hyperlink" in rule_ids
    assert "asset_broken_script" in rule_ids


def test_validator_broken_css_syntax():
    """Verify validator flags unbalanced braces and unclosed comments in CSS."""
    validator = WebsiteValidatorTool()
    files = [
        FileArtifact(
            file_path="index.html",
            content="<!DOCTYPE html><html><head><title>T</title><link rel='stylesheet' href='styles.css'></head><body></body></html>",
            language="html",
        ),
        FileArtifact(
            file_path="styles.css",
            content="body { margin: 0; /* unclosed comment",
            language="css",
        ),
    ]
    res = validator.validate(files)

    assert res.is_valid is False
    assert res.css_ok is False
    rule_ids = [d.rule_id for d in res.diagnostics]
    assert "css_unbalanced_brackets" in rule_ids or "css_unclosed_comment" in rule_ids


def test_validator_broken_javascript_syntax():
    """Verify validator flags unbalanced delimiters in JavaScript."""
    validator = WebsiteValidatorTool()
    files = [
        FileArtifact(
            file_path="index.html",
            content="<!DOCTYPE html><html><head><title>T</title><script src='script.js'></script></head><body></body></html>",
            language="html",
        ),
        FileArtifact(
            file_path="script.js",
            content="function broken( { return 1; }",
            language="javascript",
        ),
    ]
    res = validator.validate(files)

    assert res.is_valid is False
    assert res.js_ok is False
    assert any(d.rule_id == "js_syntax_delimiter_error" for d in res.diagnostics)


@pytest.mark.asyncio
async def test_validator_async():
    """Verify asynchronous validation."""
    validator = WebsiteValidatorTool()
    res = await validator.avalidate(_valid_project())
    assert res.is_valid is True
