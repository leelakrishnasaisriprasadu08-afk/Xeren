"""Xeren Research Plugin."""

from xeren.plugins.research.manifest import RESEARCH_PLUGIN_MANIFEST
from xeren.plugins.research.plugin import ResearchPlugin
from xeren.plugins.research.schemas import (
    EvidenceItem,
    KeyFinding,
    RankedSource,
    RawSearchResult,
    ResearchDepth,
    ResearchInput,
    ResearchResult,
    SearchQuery,
)
from xeren.plugins.research.tools import (
    BaseLiveSearchEngine,
    BaseSearchEngine,
    BraveSearchEngine,
    GenericHttpSearchEngine,
    MockSearchEngine,
    SearchAdapter,
    SearchAuthError,
    SearchConfig,
    SearchProvider,
    SearchProviderError,
    SearchRateLimitError,
    SearchTimeoutError,
    SearxngSearchEngine,
    TavilySearchEngine,
    create_search_engine,
)

__all__ = [
    "ResearchPlugin",
    "RESEARCH_PLUGIN_MANIFEST",
    "ResearchInput",
    "ResearchResult",
    "ResearchDepth",
    "SearchQuery",
    "RawSearchResult",
    "RankedSource",
    "EvidenceItem",
    "KeyFinding",
    "BaseSearchEngine",
    "MockSearchEngine",
    "SearchAdapter",
    "BaseLiveSearchEngine",
    "TavilySearchEngine",
    "BraveSearchEngine",
    "SearxngSearchEngine",
    "GenericHttpSearchEngine",
    "create_search_engine",
    "SearchConfig",
    "SearchProvider",
    "SearchProviderError",
    "SearchAuthError",
    "SearchRateLimitError",
    "SearchTimeoutError",
]
