"""Tests for WebsiteGeneratorTool."""

import pytest

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.website.schemas import WebsiteSpecification
from xeren.plugins.website.tools.generator import WebsiteGeneratorTool


def test_generator_single_page_project():
    """Verify single-page website project generates index.html, styles.css, and script.js."""
    generator = WebsiteGeneratorTool()
    spec = WebsiteSpecification(
        site_purpose="AI Agent Platform",
        pages=["index.html"],
        sections=["Hero", "Features", "Footer"],
        features=["Fast Streaming", "Modular Architecture"],
    )

    files = generator.generate_project(spec)
    file_map = {f.file_path: f for f in files}

    assert "index.html" in file_map
    assert "styles.css" in file_map
    assert "script.js" in file_map

    # Inspect index.html
    html_content = file_map["index.html"].content
    assert "<!DOCTYPE html>" in html_content
    assert '<html lang="en">' in html_content
    assert '<link rel="stylesheet" href="styles.css">' in html_content
    assert '<script src="script.js"></script>' in html_content
    assert "AI Agent Platform" in html_content
    assert "Fast Streaming" in html_content

    # Inspect styles.css
    css_content = file_map["styles.css"].content
    assert ":root" in css_content
    assert "--primary-color" in css_content
    assert "@media (max-width: 768px)" in css_content

    # Inspect script.js
    js_content = file_map["script.js"].content
    assert "DOMContentLoaded" in js_content


def test_generator_multi_page_project():
    """Verify multi-page website project generates each requested HTML page."""
    generator = WebsiteGeneratorTool()
    spec = WebsiteSpecification(
        site_purpose="Cloud Consulting Firm",
        pages=["index.html", "services.html", "contact.html"],
        sections=["Hero", "Features"],
    )

    files = generator.generate_project(spec)
    file_paths = [f.file_path for f in files]

    assert "index.html" in file_paths
    assert "services.html" in file_paths
    assert "contact.html" in file_paths
    assert "styles.css" in file_paths
    assert "script.js" in file_paths

    # Verify cross-navigation links
    file_map = {f.file_path: f for f in files}
    services_html = file_map["services.html"].content
    assert 'href="index.html"' in services_html
    assert 'href="services.html"' in services_html
    assert 'href="contact.html"' in services_html


@pytest.mark.asyncio
async def test_generator_async_generation():
    """Verify asynchronous project generation."""
    generator = WebsiteGeneratorTool()
    spec = WebsiteSpecification(
        site_purpose="Developer Blog",
        pages=["index.html"],
    )

    files = await generator.agenerate_project(spec)
    assert len(files) >= 3
    paths = [f.file_path for f in files]
    assert "index.html" in paths
    assert "styles.css" in paths
    assert "script.js" in paths
