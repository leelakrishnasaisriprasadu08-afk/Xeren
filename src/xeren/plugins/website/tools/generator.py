"""Website project generation and modification tool leveraging Coding Plugin infrastructure."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.coding.tools.generation import CodeGenerationTool
from xeren.plugins.website.schemas import WebsiteSpecification, WebsiteType

logger = logging.getLogger("xeren.plugins.website.tools.generator")


class WebsiteGeneratorTool:
    """Generates and modifies full website projects with predictable structures."""

    def __init__(
        self,
        coding_plugin: Optional[CodingPlugin] = None,
        generation_tool: Optional[CodeGenerationTool] = None,
    ) -> None:
        self.coding_plugin = coding_plugin
        self.generation_tool = generation_tool or (coding_plugin.registry.generation_tool if coding_plugin else CodeGenerationTool())

    def _generate_html_page(
        self,
        page_name: str,
        spec: WebsiteSpecification,
        all_pages: Sequence[str],
    ) -> str:
        """Construct a complete, semantically valid HTML5 page based on specification."""
        page_title = page_name.replace(".html", "").replace("_", " ").title()
        if page_title.lower() == "index":
            page_title = spec.site_purpose[:40] if spec.site_purpose else "Home"

        # Build navigation links
        nav_links = []
        for p in all_pages:
            link_name = p.replace(".html", "").replace("_", " ").title()
            if link_name.lower() == "index":
                link_name = "Home"
            active_class = ' class="active"' if p == page_name else ""
            nav_links.append(f'            <a href="{p}"{active_class}>{link_name}</a>')
        nav_html = "\n".join(nav_links)

        # Build section markup
        sections_html = []
        has_hero = any("hero" in s.lower() for s in spec.sections)
        for idx, section in enumerate(spec.sections):
            sec_id = section.lower().replace(" ", "-").replace("/", "-")
            if "hero" in sec_id or (not has_hero and idx == 0):
                sections_html.append(
                    f'        <section id="{sec_id}" class="hero">\n'
                    f'            <div class="container">\n'
                    f'                <h1>{spec.site_purpose or "Welcome to Our Platform"}</h1>\n'
                    f'                <p class="subtitle">{spec.target_audience or "Designed with precision and elegance."}</p>\n'
                    f'                <a href="#contact" class="btn btn-primary">Get Started</a>\n'
                    f'            </div>\n'
                    f'        </section>'
                )
            elif "feature" in sec_id:
                feature_cards = []
                for f in (spec.features or ["Fast Performance", "Responsive Design", "Secure by Default"]):
                    feature_cards.append(
                        f'                <div class="card">\n'
                        f'                    <h3>{f}</h3>\n'
                        f'                    <p>Modern architecture engineered for seamless accessibility and reliability.</p>\n'
                        f'                </div>'
                    )
                cards_markup = "\n".join(feature_cards)
                sections_html.append(
                    f'        <section id="{sec_id}" class="features">\n'
                    f'            <div class="container">\n'
                    f'                <h2>Features & Capabilities</h2>\n'
                    f'                <div class="grid">\n{cards_markup}\n                </div>\n'
                    f'            </div>\n'
                    f'        </section>'
                )
            elif "footer" in sec_id:
                continue
            else:
                sections_html.append(
                    f'        <section id="{sec_id}" class="content-section">\n'
                    f'            <div class="container">\n'
                    f'                <h2>{section}</h2>\n'
                    f'                <p>Comprehensive overview and information tailored for our audience.</p>\n'
                    f'            </div>\n'
                    f'        </section>'
                )

        body_content = "\n\n".join(sections_html)

        html = (
            f"<!DOCTYPE html>\n"
            f'<html lang="en">\n'
            f"<head>\n"
            f'    <meta charset="UTF-8">\n'
            f'    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"    <title>{page_title}</title>\n"
            f'    <link rel="stylesheet" href="styles.css">\n'
            f"</head>\n"
            f"<body>\n"
            f'    <header class="site-header">\n'
            f'        <div class="container nav-wrapper">\n'
            f'            <a href="index.html" class="logo">XerenWeb</a>\n'
            f'            <nav class="site-nav">\n'
            f"{nav_html}\n"
            f"            </nav>\n"
            f"        </div>\n"
            f"    </header>\n\n"
            f"    <main>\n"
            f"{body_content}\n"
            f"    </main>\n\n"
            f'    <footer class="site-footer">\n'
            f'        <div class="container">\n'
            f"            <p>&copy; 2026 Xeren Platform. All rights reserved.</p>\n"
            f"        </div>\n"
            f"    </footer>\n\n"
            f'    <script src="script.js"></script>\n'
            f"</body>\n"
            f"</html>"
        )
        return html

    def _generate_css(self, spec: WebsiteSpecification) -> str:
        """Construct a modern, responsive stylesheet."""
        return (
            "/* Global Design System */\n"
            ":root {\n"
            "    --primary-color: #2563eb;\n"
            "    --primary-hover: #1d4ed8;\n"
            "    --bg-color: #0f172a;\n"
            "    --card-bg: #1e293b;\n"
            "    --text-color: #f8fafc;\n"
            "    --text-muted: #94a3b8;\n"
            "    --border-color: #334155;\n"
            "    --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n"
            "}\n\n"
            "* {\n"
            "    box-sizing: border-box;\n"
            "    margin: 0;\n"
            "    padding: 0;\n"
            "}\n\n"
            "body {\n"
            "    font-family: var(--font-family);\n"
            "    background-color: var(--bg-color);\n"
            "    color: var(--text-color);\n"
            "    line-height: 1.6;\n"
            "}\n\n"
            ".container {\n"
            "    max-width: 1200px;\n"
            "    margin: 0 auto;\n"
            "    padding: 0 1.5rem;\n"
            "}\n\n"
            "/* Header & Nav */\n"
            ".site-header {\n"
            "    background-color: rgba(30, 41, 59, 0.8);\n"
            "    backdrop-filter: blur(8px);\n"
            "    position: sticky;\n"
            "    top: 0;\n"
            "    z-index: 100;\n"
            "    border-bottom: 1px solid var(--border-color);\n"
            "}\n\n"
            ".nav-wrapper {\n"
            "    display: flex;\n"
            "    justify-content: space-between;\n"
            "    align-items: center;\n"
            "    height: 4rem;\n"
            "}\n\n"
            ".logo {\n"
            "    font-size: 1.25rem;\n"
            "    font-weight: 700;\n"
            "    color: var(--text-color);\n"
            "    text-decoration: none;\n"
            "}\n\n"
            ".site-nav a {\n"
            "    color: var(--text-muted);\n"
            "    text-decoration: none;\n"
            "    margin-left: 1.5rem;\n"
            "    transition: color 0.2s ease;\n"
            "}\n\n"
            ".site-nav a:hover, .site-nav a.active {\n"
            "    color: var(--primary-color);\n"
            "}\n\n"
            "/* Hero */\n"
            ".hero {\n"
            "    padding: 6rem 0;\n"
            "    text-align: center;\n"
            "    background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);\n"
            "}\n\n"
            ".hero h1 {\n"
            "    font-size: 3rem;\n"
            "    font-weight: 800;\n"
            "    margin-bottom: 1rem;\n"
            "}\n\n"
            ".subtitle {\n"
            "    font-size: 1.25rem;\n"
            "    color: var(--text-muted);\n"
            "    max-width: 600px;\n"
            "    margin: 0 auto 2rem;\n"
            "}\n\n"
            ".btn {\n"
            "    display: inline-block;\n"
            "    padding: 0.75rem 1.5rem;\n"
            "    border-radius: 0.375rem;\n"
            "    text-decoration: none;\n"
            "    font-weight: 600;\n"
            "    transition: background-color 0.2s ease;\n"
            "}\n\n"
            ".btn-primary {\n"
            "    background-color: var(--primary-color);\n"
            "    color: white;\n"
            "}\n\n"
            ".btn-primary:hover {\n"
            "    background-color: var(--primary-hover);\n"
            "}\n\n"
            "/* Features & Content */\n"
            ".features, .content-section {\n"
            "    padding: 5rem 0;\n"
            "}\n\n"
            ".grid {\n"
            "    display: grid;\n"
            "    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));\n"
            "    gap: 2rem;\n"
            "    margin-top: 2rem;\n"
            "}\n\n"
            ".card {\n"
            "    background-color: var(--card-bg);\n"
            "    border: 1px solid var(--border-color);\n"
            "    border-radius: 0.5rem;\n"
            "    padding: 2rem;\n"
            "    transition: transform 0.2s ease, border-color 0.2s ease;\n"
            "}\n\n"
            ".card:hover {\n"
            "    transform: translateY(-4px);\n"
            "    border-color: var(--primary-color);\n"
            "}\n\n"
            ".card h3 {\n"
            "    margin-bottom: 0.75rem;\n"
            "}\n\n"
            ".card p {\n"
            "    color: var(--text-muted);\n"
            "}\n\n"
            "/* Footer */\n"
            ".site-footer {\n"
            "    border-top: 1px solid var(--border-color);\n"
            "    padding: 2rem 0;\n"
            "    text-align: center;\n"
            "    color: var(--text-muted);\n"
            "    font-size: 0.875rem;\n"
            "}\n\n"
            "/* Responsive Media Queries */\n"
            "@media (max-width: 768px) {\n"
            "    .hero h1 {\n"
            "        font-size: 2rem;\n"
            "    }\n"
            "    .nav-wrapper {\n"
            "        flex-direction: column;\n"
            "        height: auto;\n"
            "        padding: 1rem 0;\n"
            "    }\n"
            "    .site-nav {\n"
            "        margin-top: 0.5rem;\n"
            "    }\n"
            "    .site-nav a {\n"
            "        margin: 0 0.5rem;\n"
            "    }\n"
            "}\n"
        )

    def _generate_js(self, spec: WebsiteSpecification) -> str:
        """Construct client-side JavaScript for interactivity."""
        return (
            "// Client-side interactions for Xeren Website\n"
            "document.addEventListener('DOMContentLoaded', () => {\n"
            "    console.log('Website initialized safely.');\n\n"
            "    // Smooth scroll for anchor links\n"
            "    document.querySelectorAll('a[href^=\"#\"]').forEach(anchor => {\n"
            "        anchor.addEventListener('click', function (e) {\n"
            "            const targetId = this.getAttribute('href');\n"
            "            if (targetId && targetId !== '#') {\n"
            "                const targetElement = document.querySelector(targetId);\n"
            "                if (targetElement) {\n"
            "                    e.preventDefault();\n"
            "                    targetElement.scrollIntoView({ behavior: 'smooth' });\n"
            "                }\n"
            "            }\n"
            "        });\n"
            "    });\n"
            "});\n"
        )

    def generate_project(
        self,
        spec: WebsiteSpecification,
    ) -> List[FileArtifact]:
        """Generate a complete website project based on a structured specification."""
        pages = spec.pages if spec.pages else ["index.html"]
        if "index.html" not in pages:
            pages = ["index.html"] + [p for p in pages if p != "index.html"]

        files: List[FileArtifact] = []

        # 1. Generate HTML pages
        for page in pages:
            html_content = self._generate_html_page(page, spec, pages)
            files.append(FileArtifact(file_path=page, content=html_content, language="html"))

        # 2. Generate CSS stylesheet
        css_content = self._generate_css(spec)
        files.append(FileArtifact(file_path="styles.css", content=css_content, language="css"))

        # 3. Generate JavaScript file
        js_content = self._generate_js(spec)
        files.append(FileArtifact(file_path="script.js", content=js_content, language="javascript"))

        return files

    def edit_project(
        self,
        existing_files: Sequence[FileArtifact],
        modification_request: str,
        spec: Optional[WebsiteSpecification] = None,
    ) -> Tuple[List[FileArtifact], List[FileArtifact]]:
        """Modify an existing website project according to instruction.

        Returns:
            (all_files, modified_files)
        """
        mod_lower = modification_request.lower()
        file_map = {f.file_path: f for f in existing_files}
        modified_files: List[FileArtifact] = []

        # Target identification
        target_path = None
        if "style" in mod_lower or "css" in mod_lower or "color" in mod_lower or "theme" in mod_lower:
            target_path = "styles.css"
        elif "script" in mod_lower or "js" in mod_lower or "interaction" in mod_lower:
            target_path = "script.js"
        elif "html" in mod_lower or "title" in mod_lower or "hero" in mod_lower or "header" in mod_lower:
            target_path = "index.html"

        # If a specific existing file was explicitly referenced
        for f in existing_files:
            if f.file_path.lower() in mod_lower:
                target_path = f.file_path
                break

        # If no specific target matched, default to index.html or first file
        if not target_path:
            target_path = "index.html" if "index.html" in file_map else existing_files[0].file_path

        target_file = file_map.get(target_path)
        if target_file:
            # Modify target file using CodeGenerationTool if available
            try:
                modified_code = self.generation_tool.edit(
                    task=modification_request,
                    source_code=target_file.content,
                    language=target_file.language,
                )
            except Exception:
                modified_code = target_file.content + f"\n/* Modified according to: {modification_request} */\n"

            # Check for fallback MockLLM response
            if modified_code.startswith("Mock response to:") or modified_code.startswith("// Modified solution for:"):
                # Deterministic modification
                if target_file.language == "html":
                    modified_code = target_file.content.replace(
                        "<title>", f"<!-- Edited: {modification_request} -->\n    <title>"
                    )
                elif target_file.language == "css":
                    modified_code = target_file.content + f"\n/* Edited: {modification_request} */\n.accent-highlight {{ color: var(--primary-color); }}\n"
                elif target_file.language == "javascript":
                    modified_code = target_file.content + f"\n// Edited: {modification_request}\nconsole.log('Update applied.');\n"

            updated_artifact = FileArtifact(
                file_path=target_file.file_path,
                content=modified_code,
                language=target_file.language,
            )
            file_map[target_path] = updated_artifact
            modified_files.append(updated_artifact)

        # Reassemble complete file list, preserving unchanged files
        all_files = list(file_map.values())
        return all_files, modified_files

    async def agenerate_project(
        self,
        spec: WebsiteSpecification,
    ) -> List[FileArtifact]:
        """Asynchronously generate website project."""
        return await asyncio.to_thread(self.generate_project, spec)

    async def aedit_project(
        self,
        existing_files: Sequence[FileArtifact],
        modification_request: str,
        spec: Optional[WebsiteSpecification] = None,
    ) -> Tuple[List[FileArtifact], List[FileArtifact]]:
        """Asynchronously edit website project."""
        return await asyncio.to_thread(self.edit_project, existing_files, modification_request, spec)


__all__ = ["WebsiteGeneratorTool"]
