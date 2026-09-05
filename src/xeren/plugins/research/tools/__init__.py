"""Internal tools for the Xeren Research Plugin."""

from xeren.plugins.research.tools.base import BaseResearchTool
from xeren.plugins.research.tools.evidence import EvidenceExtractionTool
from xeren.plugins.research.tools.live_search import (
    BaseLiveSearchEngine,
    BraveSearchEngine,
    GenericHttpSearchEngine,
    SearxngSearchEngine,
    TavilySearchEngine,
    create_search_engine,
)
from xeren.plugins.research.tools.ranking import SourceRankingTool
from xeren.plugins.research.tools.registry import ResearchToolRegistry
from xeren.plugins.research.tools.search import BaseSearchEngine, MockSearchEngine, SearchAdapter
from xeren.plugins.research.tools.search_config import (
    SearchAuthError,
    SearchConfig,
    SearchProvider,
    SearchProviderError,
    SearchRateLimitError,
    SearchTimeoutError,
    mask_api_key,
    sanitize_message,
)
from xeren.plugins.research.tools.synthesis import SynthesisTool

__all__ = [
    "BaseResearchTool",
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
    "mask_api_key",
    "sanitize_message",
    "SourceRankingTool",
    "EvidenceExtractionTool",
    "SynthesisTool",
    "ResearchToolRegistry",
]
