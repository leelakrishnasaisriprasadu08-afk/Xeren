"""Website validation tool verifying structural integrity, HTML, CSS, JS, and asset links."""

import asyncio
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from xeren.plugins.coding.schemas import Diagnostic, DiagnosticSeverity, FileArtifact
from xeren.plugins.coding.tools.syntax import SyntaxCheckTool
from xeren.plugins.website.schemas import ValidationResult

logger = logging.getLogger("xeren.plugins.website.tools.validator")


class WebsiteValidatorTool:
    """Validates website structure, HTML standards, CSS styling, and JavaScript logic."""

    def __init__(self, syntax_tool: Optional[SyntaxCheckTool] = None) -> None:
        self.syntax_tool = syntax_tool or SyntaxCheckTool()

    def validate(self, files: Sequence[FileArtifact]) -> ValidationResult:
        """Run structural and syntactic validation across all website project files."""
        diagnostics: List[Diagnostic] = []
        structure_ok = True
        html_ok = True
        css_ok = True
        js_ok = True
        assets_ok = True

        file_map = {f.file_path: f for f in files}
        file_paths_set: Set[str] = set(file_map.keys())

        # ---------------------------------------------------------------------
        # 1. Structure Validation
        # ---------------------------------------------------------------------
        # Check required entrypoint
        if not any(f.lower() in ("index.html", "index.htm", "main.html") for f in file_paths_set):
            structure_ok = False
            diagnostics.append(
                Diagnostic(
                    message="Missing required website entrypoint file ('index.html').",
                    severity=DiagnosticSeverity.ERROR,
                    rule_id="web_missing_entrypoint",
                    file_path="index.html",
                )
            )

        # Check for path traversal in file paths
        for fp in file_paths_set:
            norm_p = Path(fp)
            if ".." in norm_p.parts or fp.startswith("/") or fp.startswith("\\") or ":" in fp:
                structure_ok = False
                diagnostics.append(
                    Diagnostic(
                        message=f"Path traversal or invalid absolute path detected: '{fp}'.",
                        severity=DiagnosticSeverity.ERROR,
                        rule_id="web_path_traversal",
                        file_path=fp,
                    )
                )

        # ---------------------------------------------------------------------
        # 2. File-by-File Content Validation
        # ---------------------------------------------------------------------
        for f in files:
            ext = Path(f.file_path).suffix.lower()
            lang = f.language.lower()

            if ext == ".html" or lang == "html":
                page_html_ok, page_asset_ok, page_diags = self._validate_html(f, file_paths_set)
                if not page_html_ok:
                    html_ok = False
                if not page_asset_ok:
                    assets_ok = False
                diagnostics.extend(page_diags)

            elif ext == ".css" or lang == "css":
                page_css_ok, page_diags = self._validate_css(f)
                if not page_css_ok:
                    css_ok = False
                diagnostics.extend(page_diags)

            elif ext in (".js", ".mjs") or lang in ("javascript", "js"):
                page_js_ok, page_diags = self._validate_js(f)
                if not page_js_ok:
                    js_ok = False
                diagnostics.extend(page_diags)

        # Overall validity
        is_valid = structure_ok and html_ok and css_ok and js_ok and assets_ok

        return ValidationResult(
            is_valid=is_valid,
            structure_ok=structure_ok,
            html_ok=html_ok,
            css_ok=css_ok,
            js_ok=js_ok,
            assets_ok=assets_ok,
            diagnostics=diagnostics,
            details={
                "total_files": len(files),
                "structure_errors": sum(1 for d in diagnostics if d.rule_id and d.rule_id.startswith("web_missing") or d.rule_id == "web_path_traversal"),
                "html_errors": sum(1 for d in diagnostics if d.rule_id and d.rule_id.startswith("html_")),
                "css_errors": sum(1 for d in diagnostics if d.rule_id and d.rule_id.startswith("css_")),
                "js_errors": sum(1 for d in diagnostics if d.rule_id and d.rule_id.startswith("js_")),
                "asset_errors": sum(1 for d in diagnostics if d.rule_id and d.rule_id.startswith("asset_")),
            },
        )

    def _validate_html(
        self,
        artifact: FileArtifact,
        all_project_files: Set[str],
    ) -> Tuple[bool, bool, List[Diagnostic]]:
        """Validate HTML structure, tags, and local references."""
        html_ok = True
        assets_ok = True
        diags: List[Diagnostic] = []
        content = artifact.content
        content_lower = content.lower()

        # Check basic document structure for HTML pages
        if "<html" not in content_lower:
            html_ok = False
            diags.append(
                Diagnostic(
                    message="HTML document is missing <html> root element.",
                    severity=DiagnosticSeverity.ERROR,
                    rule_id="html_missing_root",
                    file_path=artifact.file_path,
                )
            )

        if "<head" not in content_lower or "</head>" not in content_lower:
            html_ok = False
            diags.append(
                Diagnostic(
                    message="HTML document is missing <head> element or closing </head>.",
                    severity=DiagnosticSeverity.ERROR,
                    rule_id="html_missing_head",
                    file_path=artifact.file_path,
                )
            )

        if "<body" not in content_lower or "</body>" not in content_lower:
            html_ok = False
            diags.append(
                Diagnostic(
                    message="HTML document is missing <body> element or closing </body>.",
                    severity=DiagnosticSeverity.ERROR,
                    rule_id="html_missing_body",
                    file_path=artifact.file_path,
                )
            )

        # Check tag balance for critical tags
        for tag in ("title", "main", "header", "footer"):
            open_count = len(re.findall(rf"<{tag}\b[^>]*>", content_lower))
            close_count = len(re.findall(rf"</{tag}>", content_lower))
            if open_count != close_count:
                html_ok = False
                diags.append(
                    Diagnostic(
                        message=f"Mismatched <{tag}> tag count: {open_count} open vs {close_count} close.",
                        severity=DiagnosticSeverity.ERROR,
                        rule_id=f"html_unclosed_{tag}",
                        file_path=artifact.file_path,
                    )
                )

        # Reference and link checking
        # 1. Stylesheet links: <link ... href="..." ...>
        link_hrefs = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for href in link_hrefs:
            if not self._is_external_or_special_link(href):
                clean_ref = href.split("#")[0].split("?")[0]
                if clean_ref and clean_ref not in all_project_files:
                    assets_ok = False
                    diags.append(
                        Diagnostic(
                            message=f"Broken stylesheet reference: '{href}' not found in project.",
                            severity=DiagnosticSeverity.ERROR,
                            rule_id="asset_broken_stylesheet",
                            file_path=artifact.file_path,
                        )
                    )

        # 2. Scripts: <script ... src="..." ...>
        script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for src in script_srcs:
            if not self._is_external_or_special_link(src):
                clean_ref = src.split("#")[0].split("?")[0]
                if clean_ref and clean_ref not in all_project_files:
                    assets_ok = False
                    diags.append(
                        Diagnostic(
                            message=f"Broken script reference: '{src}' not found in project.",
                            severity=DiagnosticSeverity.ERROR,
                            rule_id="asset_broken_script",
                            file_path=artifact.file_path,
                        )
                    )

        # 3. Images: <img ... src="..." ...>
        img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for src in img_srcs:
            if not self._is_external_or_special_link(src):
                clean_ref = src.split("#")[0].split("?")[0]
                if clean_ref and clean_ref not in all_project_files:
                    assets_ok = False
                    diags.append(
                        Diagnostic(
                            message=f"Broken image reference: '{src}' not found in project.",
                            severity=DiagnosticSeverity.ERROR,
                            rule_id="asset_broken_image",
                            file_path=artifact.file_path,
                        )
                    )

        # 4. Anchor links: <a ... href="..." ...>
        a_hrefs = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for href in a_hrefs:
            if not self._is_external_or_special_link(href):
                clean_ref = href.split("#")[0].split("?")[0]
                if clean_ref and clean_ref not in all_project_files:
                    assets_ok = False
                    diags.append(
                        Diagnostic(
                            message=f"Broken internal hyperlink reference: '{href}' not found in project.",
                            severity=DiagnosticSeverity.ERROR,
                            rule_id="asset_broken_hyperlink",
                            file_path=artifact.file_path,
                        )
                    )

        return html_ok, assets_ok, diags

    def _validate_css(self, artifact: FileArtifact) -> Tuple[bool, List[Diagnostic]]:
        """Validate CSS bracket balance and basic syntax."""
        css_ok = True
        diags: List[Diagnostic] = []

        # Check bracket balance using Coding Plugin's SyntaxCheckTool
        is_balanced, balance_diags = self.syntax_tool.check_bracket_balance(
            artifact.content, file_path=artifact.file_path
        )
        if not is_balanced:
            css_ok = False
            for d in balance_diags:
                diags.append(
                    Diagnostic(
                        message=f"CSS syntax error: {d.message}",
                        severity=DiagnosticSeverity.ERROR,
                        line=d.line,
                        column=d.column,
                        rule_id="css_unbalanced_brackets",
                        file_path=artifact.file_path,
                    )
                )

        # Check for unclosed /* comment blocks */
        open_comments = artifact.content.count("/*")
        close_comments = artifact.content.count("*/")
        if open_comments != close_comments:
            css_ok = False
            diags.append(
                Diagnostic(
                    message=f"Unclosed CSS comment block: {open_comments} open vs {close_comments} close.",
                    severity=DiagnosticSeverity.ERROR,
                    rule_id="css_unclosed_comment",
                    file_path=artifact.file_path,
                )
            )

        return css_ok, diags

    def _validate_js(self, artifact: FileArtifact) -> Tuple[bool, List[Diagnostic]]:
        """Validate JavaScript syntax and bracket balance."""
        js_ok = True
        diags: List[Diagnostic] = []

        # Check bracket balance using SyntaxCheckTool
        is_balanced, balance_diags = self.syntax_tool.check_bracket_balance(
            artifact.content, file_path=artifact.file_path
        )
        if not is_balanced:
            js_ok = False
            for d in balance_diags:
                diags.append(
                    Diagnostic(
                        message=f"JavaScript syntax error: {d.message}",
                        severity=DiagnosticSeverity.ERROR,
                        line=d.line,
                        column=d.column,
                        rule_id="js_syntax_delimiter_error",
                        file_path=artifact.file_path,
                    )
                )

        return js_ok, diags

    @staticmethod
    def _is_external_or_special_link(link: str) -> bool:
        """Check if link is an external URL, anchor bookmark, data URI, or mailto/tel link."""
        trimmed = link.strip().lower()
        if not trimmed:
            return True
        if trimmed.startswith(("#", "http://", "https://", "//", "mailto:", "tel:", "data:", "javascript:")):
            return True
        return False

    async def avalidate(self, files: Sequence[FileArtifact]) -> ValidationResult:
        """Asynchronously validate website files."""
        return await asyncio.to_thread(self.validate, files)


__all__ = ["WebsiteValidatorTool"]
