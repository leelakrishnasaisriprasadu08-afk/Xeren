"""
Pluggable web search. Ships with a generic adapter for Serper.dev-style
JSON search APIs; swap `search()` internals for Bing/SerpAPI/Google CSE as
needed -- the rest of the framework only ever calls `.search()`.

If no SEARCH_API_KEY is configured, `.search()` returns an empty list
instead of raising, so plugins that treat web search as "nice to have"
keep working without one.
"""
from typing import Any, Dict, List

import requests

from ..config import settings


class WebSearchTool:
    def __init__(self, api_key: str = None, api_url: str = None):
        self.api_key = api_key or settings.search_api_key
        self.api_url = api_url or settings.search_api_url

    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        if not self.available():
            return []
        try:
            resp = requests.post(
                self.api_url,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json={"q": query, "num": num_results},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            print(f"[web_search] '{query}' failed: {exc}")
            return []
        return data.get("organic", [])[:num_results]

    @staticmethod
    def summarize_results(results: List[Dict[str, Any]]) -> str:
        lines = []
        for r in results:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            lines.append(f"- {title}: {snippet} ({link})")
        return "\n".join(lines)
