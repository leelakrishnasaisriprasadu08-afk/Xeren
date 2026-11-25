"""Deterministic Browser and Web Interaction Tools.

Enables opening browser tabs, scraping clean text from pages, and zero-API-key
search retrieval deterministically.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Dict, List, Optional

logger = logging.getLogger("xeren.tools.deterministic.browser")


class DeterministicBrowserTools:
    """Controls browser navigation and clean HTML-to-text extraction deterministically."""

    def __init__(self, user_agent: Optional[str] = None) -> None:
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

    def open_tab(self, url: str) -> Dict[str, Any]:
        """Open a URL in the user's default desktop web browser."""
        clean_url = url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "https://" + clean_url

        try:
            opened = webbrowser.open(clean_url, new=2)  # new=2 -> open in new tab if possible
            return {
                "success": opened,
                "url": clean_url,
                "message": f"Opened tab for {clean_url}",
            }
        except Exception as e:
            logger.error("Failed to open tab for %s: %s", clean_url, e)
            return {
                "success": False,
                "error": str(e),
                "url": clean_url,
            }

    def fetch_page_text(self, url: str, timeout: float = 15.0, max_chars: int = 100_000) -> Dict[str, Any]:
        """Deterministically fetch web page and convert HTML into clean readable text."""
        clean_url = url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "https://" + clean_url

        req = urllib.request.Request(
            clean_url,
            headers={"User-Agent": self.user_agent},
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw_bytes = response.read(max_chars * 4)
                charset = response.headers.get_content_charset() or "utf-8"
                raw_html = raw_bytes.decode(charset, errors="replace")

            # Extract title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
            title = html.unescape(title_match.group(1).strip()) if title_match else ""

            # Remove scripts, styles, head, nav, footer
            clean_html = re.sub(r"<(script|style|head|nav|footer)[^>]*>.*?</\1>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
            # Remove all other HTML tags
            text = re.sub(r"<[^>]+>", " ", clean_html)
            # Unescape HTML entities
            text = html.unescape(text)
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text).strip()

            if len(text) > max_chars:
                text = text[:max_chars] + "...[truncated]"

            return {
                "success": True,
                "url": clean_url,
                "title": title,
                "content": text,
                "length": len(text),
            }
        except Exception as e:
            logger.warning("Error fetching web page %s: %s", clean_url, e)
            return {
                "success": False,
                "url": clean_url,
                "error": str(e),
                "content": "",
            }

    def search_duckduckgo_lite(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Perform zero-API-key web search using DuckDuckGo HTML endpoint."""
        clean_q = query.strip()
        encoded_q = urllib.parse.urlencode({"q": clean_q})
        search_url = f"https://html.duckduckgo.com/html/?{encoded_q}"

        fetch_res = self.fetch_page_text(search_url, timeout=12.0)
        if not fetch_res["success"]:
            return {
                "success": False,
                "query": clean_q,
                "error": fetch_res.get("error", "Failed to retrieve search results"),
                "results": [],
            }

        # Extract search snippets
        content = fetch_res["content"]
        # Basic snippet segmentation
        parts = content.split("...")
        snippets = [p.strip() for p in parts if len(p.strip()) > 30][:max_results]

        return {
            "success": True,
            "query": clean_q,
            "count": len(snippets),
            "snippets": snippets,
            "raw_text": content[:2000],
        }


# Singleton instance
default_browser = DeterministicBrowserTools()

