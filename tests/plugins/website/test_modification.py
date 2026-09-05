"""Tests for website modification and editing capabilities."""

import pytest

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.website.tools.generator import WebsiteGeneratorTool


def _sample_existing_project():
    return [
        FileArtifact(
            file_path="index.html",
            content="<!DOCTYPE html><html><head><title>Old Title</title></head><body><h1>Hello</h1></body></html>",
            language="html",
        ),
        FileArtifact(
            file_path="styles.css",
            content="body { background-color: #ffffff; color: #000000; }",
            language="css",
        ),
        FileArtifact(
            file_path="script.js",
            content="console.log('original script');",
            language="javascript",
        ),
    ]


def test_edit_html_preserves_other_files():
    """Verify modifying HTML updates target page while preserving styles and scripts."""
    generator = WebsiteGeneratorTool()
    existing = _sample_existing_project()

    all_files, modified = generator.edit_project(
        existing_files=existing,
        modification_request="Update title and header in HTML to New Product Launch",
    )

    assert len(all_files) == 3
    assert len(modified) == 1
    assert modified[0].file_path == "index.html"

    # Verify CSS and JS remained unchanged
    file_map = {f.file_path: f for f in all_files}
    assert file_map["styles.css"].content == existing[1].content
    assert file_map["script.js"].content == existing[2].content


def test_edit_css_stylesheet():
    """Verify modifying stylesheet updates styles.css and identifies it as modified."""
    generator = WebsiteGeneratorTool()
    existing = _sample_existing_project()

    all_files, modified = generator.edit_project(
        existing_files=existing,
        modification_request="Change theme colors and background styling in css",
    )

    assert len(modified) == 1
    assert modified[0].file_path == "styles.css"
    file_map = {f.file_path: f for f in all_files}
    assert file_map["index.html"].content == existing[0].content


def test_edit_javascript():
    """Verify modifying script updates script.js."""
    generator = WebsiteGeneratorTool()
    existing = _sample_existing_project()

    all_files, modified = generator.edit_project(
        existing_files=existing,
        modification_request="Add modal popup interaction in javascript script",
    )

    assert len(modified) == 1
    assert modified[0].file_path == "script.js"


@pytest.mark.asyncio
async def test_edit_async():
    """Verify asynchronous editing workflow."""
    generator = WebsiteGeneratorTool()
    existing = _sample_existing_project()

    all_files, modified = await generator.aedit_project(
        existing_files=existing,
        modification_request="Change styles",
    )

    assert len(all_files) == 3
    assert len(modified) == 1
