"""Public exports for RAG retrieval."""

from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.retrieval.filter import FilterCondition, FilterOperator, MetadataFilter
from xeren.rag.retrieval.hybrid import HybridRetriever
from xeren.rag.retrieval.keyword import KeywordRetriever
from xeren.rag.retrieval.pattern import SovereignPatternRetriever, create_sovereign_rag_engine
from xeren.rag.retrieval.types import SearchResult

__all__ = [
    "BaseRetriever",
    "DenseRetriever",
    "KeywordRetriever",
    "HybridRetriever",
    "SovereignPatternRetriever",
    "create_sovereign_rag_engine",
    "MetadataFilter",
    "FilterCondition",
    "FilterOperator",
    "SearchResult",
]

