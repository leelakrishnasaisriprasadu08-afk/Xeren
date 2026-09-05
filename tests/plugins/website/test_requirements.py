"""Tests for RequirementAnalysisTool."""

import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.website.schemas import WebsiteSpecification, WebsiteType
from xeren.plugins.website.tools.requirements import RequirementAnalysisTool
def test_requirement_analysis_default_mock():
    """Verify default mock LLM produces a structured, high-quality specification."""
    tool = RequirementAnalysisTool()
    spec = tool.analyze("Build a landing page for an AI startup", website_type=WebsiteType.LANDING_PAGE)

    assert isinstance(spec, WebsiteSpecification)
    assert "AI startup" in spec.site_purpose
    assert "index.html" in spec.pages
    assert len(spec.sections) >= 3
    assert len(spec.features) >= 2
    assert spec.technology_choice == "html/css/js"


def test_requirement_analysis_custom_json():
    """Verify JSON output from LLM is correctly parsed into WebsiteSpecification."""
    custom_json = """{
        "site_purpose": "Next-generation Developer Tools",
        "target_audience": "Software Engineers",
        "pages": ["index.html", "docs.html"],
        "sections": ["Hero", "Code Showcase", "Pricing"],
        "features": ["Syntax highlighting", "One-click copy"],
        "content_requirements": ["High-contrast examples"],
        "technology_choice": "html/css/js",
        "responsive_requirements": ["Mobile view"],
        "accessibility_requirements": ["WCAG AA"],
        "security_requirements": ["CSP headers"]
    }"""
    llm = MockLLM(canned_response=f"```json\n{custom_json}\n```")
    tool = RequirementAnalysisTool(llm=llm)

    spec = tool.analyze("Dev tools site")
    assert spec.site_purpose == "Next-generation Developer Tools"
    assert spec.target_audience == "Software Engineers"
    assert spec.pages == ["index.html", "docs.html"]
    assert "Code Showcase" in spec.sections
    assert "Syntax highlighting" in spec.features


def test_requirement_analysis_malformed_llm_fallback():
    """Verify tool recovers gracefully with fallback specification when LLM outputs non-JSON."""
    llm = MockLLM(canned_response="I am an AI assistant and I think you should build a cool website!")
    tool = RequirementAnalysisTool(llm=llm)
    spec = tool.analyze("E-commerce storefront for books", website_type=WebsiteType.BUSINESS)

    assert isinstance(spec, WebsiteSpecification)
    assert "E-commerce storefront for books" in spec.site_purpose
    assert "index.html" in spec.pages
    assert len(spec.sections) > 0


def test_requirement_analysis_multipage_heuristic():
    """Verify requirement mentioning multiple pages detects multi-page structure."""
    tool = RequirementAnalysisTool(llm=MockLLM())
    spec = tool.analyze("Build a multi-page company site with about and contact pages")

    assert "index.html" in spec.pages
    assert "about.html" in spec.pages
    assert "contact.html" in spec.pages


@pytest.mark.asyncio
async def test_requirement_analysis_async():
    """Verify asynchronous requirement analysis."""
    tool = RequirementAnalysisTool()
    spec = await tool.aanalyze("Portfolio for a UX designer", website_type=WebsiteType.PORTFOLIO)

    assert isinstance(spec, WebsiteSpecification)
    assert "Portfolio" in spec.site_purpose
    assert "index.html" in spec.pages


def test_requirement_analysis_set_llm():
    """Verify set_llm updates the underlying provider."""
    tool = RequirementAnalysisTool()
    new_llm = MockLLM(canned_response="updated")
    tool.set_llm(new_llm)
    assert tool.llm is new_llm
