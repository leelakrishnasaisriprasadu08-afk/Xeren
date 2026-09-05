"""Requirement analysis tool converting natural language requests into structured website specifications."""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from xeren.models.base import BaseLLM
from xeren.models.providers.mock import MockLLM
from xeren.models.types import ChatMessage, Role
from xeren.plugins.website.schemas import WebsiteSpecification, WebsiteType

logger = logging.getLogger("xeren.plugins.website.tools.requirements")


class RequirementAnalysisTool:
    """Analyzes natural-language website requests and produces structured specifications."""

    def __init__(self, llm: Optional[BaseLLM] = None) -> None:
        self.llm = llm or MockLLM()

    def set_llm(self, llm: BaseLLM) -> None:
        """Inject or update the active LLM provider."""
        self.llm = llm

    @staticmethod
    def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse a JSON dictionary from LLM output, supporting code fences."""
        # 1. Look for ```json ... ``` or ``` ... ```
        pattern = r"```(?:json)?\s*\n([\s\S]*?)\n```"
        match = re.search(pattern, text, re.IGNORECASE)
        candidate = match.group(1).strip() if match else text.strip()

        # 2. Try parsing candidate directly
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # 3. Try to locate outermost { ... }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        return None

    def _build_fallback_specification(
        self,
        requirement: str,
        website_type: Union[WebsiteType, str],
        pages: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        design_requirements: Optional[List[str]] = None,
        content_requirements: Optional[List[str]] = None,
    ) -> WebsiteSpecification:
        """Build a high-fidelity deterministic specification when LLM is in mock mode or parsing fails."""
        site_type_str = website_type.value if isinstance(website_type, WebsiteType) else str(website_type)
        type_lower = site_type_str.lower()

        # Determine target pages
        target_pages = list(pages) if pages else ["index.html"]
        req_lower = requirement.lower()
        if ("multi-page" in req_lower or "multiple pages" in req_lower or "about" in req_lower) and len(target_pages) == 1:
            target_pages = ["index.html", "about.html", "contact.html"]

        # Default sections and features based on archetype
        default_sections = ["Header/Navbar", "Hero Section", "Features", "Call to Action", "Footer"]
        if "dashboard" in type_lower:
            default_sections = ["Sidebar Navigation", "Summary Metrics Cards", "Data Visualization Area", "Recent Activity Table"]
        elif "portfolio" in type_lower:
            default_sections = ["Header/Navbar", "Introduction Hero", "Projects Showcase", "Skills & Technologies", "Contact Form"]
        elif "documentation" in type_lower:
            default_sections = ["Doc Header", "Sidebar Table of Contents", "Content Article", "API Reference Section"]

        target_features = list(features) if features else [
            "Responsive layout (desktop and mobile)",
            "Interactive navigation menu",
            "Modern visual styling and smooth transitions",
        ]

        target_content = list(content_requirements) if content_requirements else [
            f"Clear value proposition for {requirement or site_type_str}",
            "Concise explanatory copy and semantic section headings",
        ]

        return WebsiteSpecification(
            site_purpose=requirement.strip() or f"Create a modern, responsive {site_type_str}",
            target_audience=f"Target users and stakeholders for {site_type_str}",
            pages=target_pages,
            sections=default_sections,
            features=target_features,
            content_requirements=target_content,
            technology_choice="html/css/js",
            responsive_requirements=["Mobile-first responsive design", "Flexible CSS Grid and Flexbox layouts"],
            accessibility_requirements=["Semantic HTML5 tags", "ARIA labels on interactive widgets", "Keyboard navigation support"],
            security_requirements=["No inline secrets or tokens", "Strict client-side input escaping", "HTTPS external assets only"],
            metadata={"source": "requirement_analysis_tool", "website_type": site_type_str},
        )

    def analyze(
        self,
        requirement: str,
        website_type: Union[WebsiteType, str] = WebsiteType.LANDING_PAGE,
        pages: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        design_requirements: Optional[List[str]] = None,
        content_requirements: Optional[List[str]] = None,
    ) -> WebsiteSpecification:
        """Analyze a natural-language website requirement and return a structured specification."""
        site_type_str = website_type.value if isinstance(website_type, WebsiteType) else str(website_type)

        prompt = (
            "You are a principal web architect. Convert the following website request into a comprehensive, "
            "production-grade specification. Return ONLY a JSON object with the following fields:\n"
            "- site_purpose: string\n"
            "- target_audience: string\n"
            "- pages: list of string filenames (e.g. ['index.html'])\n"
            "- sections: list of string section names\n"
            "- features: list of string feature descriptions\n"
            "- content_requirements: list of content copy requirements\n"
            "- technology_choice: string (e.g. 'html/css/js')\n"
            "- responsive_requirements: list of responsive design rules\n"
            "- accessibility_requirements: list of accessibility rules\n"
            "- security_requirements: list of client security rules\n\n"
            f"User Requirement: {requirement}\n"
            f"Website Type: {site_type_str}\n"
            f"Explicit Requested Pages: {pages or []}\n"
            f"Explicit Requested Features: {features or []}\n"
        )

        messages = [
            ChatMessage(role=Role.SYSTEM, content="You are an expert web architect. Output only valid JSON."),
            ChatMessage(role=Role.USER, content=prompt),
        ]

        try:
            response = self.llm.generate(messages)
            raw_content = response.content

            # Check if this is unconfigured MockLLM
            if raw_content.startswith("Mock response to:"):
                return self._build_fallback_specification(
                    requirement, website_type, pages, features, design_requirements, content_requirements
                )

            data = self.extract_json_block(raw_content)
            if not data:
                logger.warning("LLM response did not contain valid JSON; falling back to deterministic specification.")
                return self._build_fallback_specification(
                    requirement, website_type, pages, features, design_requirements, content_requirements
                )

            # Construct specification from parsed data with robust fallbacks
            return WebsiteSpecification(
                site_purpose=data.get("site_purpose", requirement),
                target_audience=data.get("target_audience", "General audience"),
                pages=data.get("pages") or (pages or ["index.html"]),
                sections=data.get("sections") or ["Header", "Hero", "Content", "Footer"],
                features=data.get("features") or (features or ["Responsive layout"]),
                content_requirements=data.get("content_requirements") or ["Standard website copy"],
                technology_choice=data.get("technology_choice", "html/css/js"),
                responsive_requirements=data.get("responsive_requirements") or ["Mobile-first design"],
                accessibility_requirements=data.get("accessibility_requirements") or ["Semantic HTML5"],
                security_requirements=data.get("security_requirements") or ["No inline credentials"],
                metadata={"parsed_from_llm": True, "website_type": site_type_str},
            )
        except Exception as err:
            logger.warning("Requirement analysis failed with error: %s; using deterministic fallback.", err)
            return self._build_fallback_specification(
                requirement, website_type, pages, features, design_requirements, content_requirements
            )

    async def aanalyze(
        self,
        requirement: str,
        website_type: Union[WebsiteType, str] = WebsiteType.LANDING_PAGE,
        pages: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        design_requirements: Optional[List[str]] = None,
        content_requirements: Optional[List[str]] = None,
    ) -> WebsiteSpecification:
        """Asynchronously analyze requirement."""
        return await asyncio.to_thread(
            self.analyze,
            requirement,
            website_type,
            pages,
            features,
            design_requirements,
            content_requirements,
        )


__all__ = ["RequirementAnalysisTool"]
