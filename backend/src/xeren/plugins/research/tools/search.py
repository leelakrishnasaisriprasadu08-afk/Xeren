"""Abstract search engine interface, mock implementation, and pluggable adapter."""

from abc import ABC, abstractmethod
import asyncio
import re
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from xeren.plugins.research.schemas import RawSearchResult


class BaseSearchEngine(ABC):
    """Abstract interface for external search providers."""

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        """Execute search query and return raw search results."""
        pass

    async def asearch(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        """Asynchronously execute search query."""
        return await asyncio.to_thread(self.search, query, max_results, domains, **kwargs)

    def ping(self) -> bool:
        """Check search provider availability."""
        return True

    async def aping(self) -> bool:
        """Asynchronously check search provider availability."""
        return await asyncio.to_thread(self.ping)


class MockSearchEngine(BaseSearchEngine):
    """Deterministic mock search engine for testing without external web calls."""

    def __init__(
        self,
        canned_results: Optional[Dict[str, List[RawSearchResult]]] = None,
        default_results: Optional[List[RawSearchResult]] = None,
        error_to_raise: Optional[Exception] = None,
        latency_seconds: float = 0.0,
        is_healthy: bool = True,
    ) -> None:
        self.canned_results = canned_results or {}
        self.default_results = default_results
        self.error_to_raise = error_to_raise
        self.latency_seconds = latency_seconds
        self.is_healthy = is_healthy
        self.query_history: List[str] = []

    def set_results(self, query: str, results: List[RawSearchResult]) -> None:
        """Register canned results for a specific query substring."""
        self.canned_results[query.lower()] = results

    def search(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        self.query_history.append(query)
        if self.latency_seconds > 0:
            time.sleep(self.latency_seconds)

        if self.error_to_raise:
            raise self.error_to_raise

        # Check canned matches
        q_lower = query.lower()
        for key, results in self.canned_results.items():
            if key in q_lower or q_lower in key:
                filtered = self._apply_domain_filter(results, domains)
                return filtered[:max_results]

        if self.default_results is not None:
            filtered = self._apply_domain_filter(self.default_results, domains)
            return filtered[:max_results]

        # Generate synthetic results based on query keywords
        slug = re.sub(r"[^\w\s-]", "", q_lower).strip().replace(" ", "-")[:40] or "query"
        base_domain = domains[0] if domains else "example.org"

        results = [
            RawSearchResult(
                url=f"https://{base_domain}/research/{slug}-overview",
                title=f"{query.title()} - Executive Analysis",
                snippet=f"Comprehensive examination of {query}, outlining foundational concepts, verified data, and primary findings.",
                full_content=f"Full detailed report regarding {query}. Section 1: Fundamental principles and background. Section 2: Recent findings and empirical data. Section 3: Industry applications and verified outcomes.",
                score=0.95,
                published_date="2026-01-15",
                author="Xeren Research Collective",
            ),
            RawSearchResult(
                url=f"https://{base_domain}/reports/{slug}-deepdive",
                title=f"Advanced Insights: {query.title()}",
                snippet=f"Empirical benchmarks and comparative evaluations concerning {query}, highlighting key performance indicators.",
                full_content=f"Detailed evaluation metrics and observational data on {query}. Performance indicators show reliable operational efficacy.",
                score=0.88,
                published_date="2026-02-01",
                author="Data Systems Review",
            ),
            RawSearchResult(
                url=f"https://{base_domain}/wiki/{slug}",
                title=f"{query.title()} Reference Guide",
                snippet=f"Reference standards, definitions, and technical parameters for {query}.",
                full_content=f"Standard reference documentation for {query}. Includes taxonomy, definitions, and historical context.",
                score=0.80,
                published_date="2025-11-20",
                author="Technical Standards Institute",
            ),
        ]
        return results[:max_results]

    async def asearch(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)
        return self.search(query, max_results=max_results, domains=domains, **kwargs)

    def ping(self) -> bool:
        if not self.is_healthy:
            return False
        if self.error_to_raise:
            return False
        return True

    def _apply_domain_filter(
        self,
        results: List[RawSearchResult],
        domains: Optional[List[str]],
    ) -> List[RawSearchResult]:
        if not domains:
            return list(results)
        return [r for r in results if any(dom.lower() in r.url.lower() for dom in domains)]


class SearchAdapter(BaseSearchEngine):
    """Adapter for wrapping arbitrary search functions or external APIs (e.g. Brave, Tavily, Google)."""

    def __init__(
        self,
        search_fn: Callable[[str, int, Optional[List[str]]], List[RawSearchResult]],
        asearch_fn: Optional[Callable[[str, int, Optional[List[str]]], Coroutine[Any, Any, List[RawSearchResult]]]] = None,
        ping_fn: Optional[Callable[[], bool]] = None,
    ) -> None:
        self._search_fn = search_fn
        self._asearch_fn = asearch_fn
        self._ping_fn = ping_fn

    def search(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        return self._search_fn(query, max_results, domains)

    async def asearch(
        self,
        query: str,
        max_results: int = 5,
        domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[RawSearchResult]:
        if self._asearch_fn is not None:
            return await self._asearch_fn(query, max_results, domains)
        return await asyncio.to_thread(self.search, query, max_results, domains, **kwargs)

    def ping(self) -> bool:
        if self._ping_fn is not None:
            return self._ping_fn()
        return True


__all__ = ["BaseSearchEngine", "MockSearchEngine", "SearchAdapter"]
