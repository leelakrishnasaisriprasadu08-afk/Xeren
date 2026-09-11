"""Public exports for the Xeren RAG subsystem."""

from xeren.rag.chunkers import (
    BaseChunker,
    CharacterChunker,
    ChunkingConfig,
    MarkdownHeaderChunker,
    RecursiveTextChunker,
)
from xeren.rag.context import Citation, ContextBuilder, ContextConfig, GroundedContext
from xeren.rag.document import Document, DocumentChunk, DocumentMetadata
from xeren.rag.embeddings import (
    BaseEmbeddingModel,
    EmbeddedChunk,
    EmbeddingConfig,
    EmbeddingRegistry,
    LocalOpenWeightEmbeddingAdapter,
    MockEmbeddingModel,
)
from xeren.rag.cag import CAGRetrievalEngine, CachedContextEntry, CachePolicy, CacheStats
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.mag import MAGRetrievalEngine, MemoryQuery, MemoryRecord, MemoryTier, RetrievedMemory
from xeren.rag.unified_engine import UnifiedAnswer, UnifiedContextPayload, UnifiedRetrievalEngine
from xeren.rag.errors import (
    ChunkingError,
    DocumentLoadingError,
    NormalizationError,
    PipelineExecutionError,
    RAGError,
    UnsupportedFormatError,
)
from xeren.rag.generator import GroundedAnswer, GroundedGenerator
from xeren.rag.loaders import (
    BaseDocumentLoader,
    DirectoryLoader,
    JSONLoader,
    LoaderRegistry,
    MarkdownLoader,
    TextFileLoader,
)
from xeren.rag.normalizers import BaseNormalizer, CompositeNormalizer, TextNormalizer
from xeren.rag.pipeline import IngestionPipeline
from xeren.rag.rerankers import (
    BaseReranker,
    CompositeReranker,
    MockReranker,
    ScoreThresholdReranker,
)
from xeren.rag.retrieval import (
    BaseRetriever,
    DenseRetriever,
    FilterCondition,
    FilterOperator,
    HybridRetriever,
    KeywordRetriever,
    MetadataFilter,
    SearchResult,
)
from xeren.rag.stores import ChromaVectorStore, InMemoryVectorStore, QdrantVectorStore, VectorStore

__all__ = [
    # Document models
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    # Ingestion & Query Pipelines
    "IngestionPipeline",
    "RAGQueryEngine",
    "CAGRetrievalEngine",
    "CachedContextEntry",
    "CachePolicy",
    "CacheStats",
    "MAGRetrievalEngine",
    "MemoryQuery",
    "MemoryRecord",
    "MemoryTier",
    "RetrievedMemory",
    "UnifiedRetrievalEngine",
    "UnifiedContextPayload",
    "UnifiedAnswer",
    "GroundedGenerator",
    "GroundedAnswer",
    # Context & Citations
    "ContextBuilder",
    "ContextConfig",
    "GroundedContext",
    "Citation",
    # Rerankers
    "BaseReranker",
    "ScoreThresholdReranker",
    "CompositeReranker",
    "MockReranker",
    # Loaders
    "BaseDocumentLoader",
    "TextFileLoader",
    "MarkdownLoader",
    "JSONLoader",
    "DirectoryLoader",
    "LoaderRegistry",
    # Normalizers
    "BaseNormalizer",
    "TextNormalizer",
    "CompositeNormalizer",
    # Chunkers
    "BaseChunker",
    "ChunkingConfig",
    "RecursiveTextChunker",
    "CharacterChunker",
    "MarkdownHeaderChunker",
    # Embeddings
    "BaseEmbeddingModel",
    "EmbeddedChunk",
    "EmbeddingConfig",
    "EmbeddingRegistry",
    "MockEmbeddingModel",
    "LocalOpenWeightEmbeddingAdapter",
    # Stores
    "VectorStore",
    "InMemoryVectorStore",
    "QdrantVectorStore",
    "ChromaVectorStore",
    # Retrieval
    "BaseRetriever",
    "DenseRetriever",
    "KeywordRetriever",
    "HybridRetriever",
    "MetadataFilter",
    "FilterCondition",
    "FilterOperator",
    "SearchResult",
    # Errors
    "RAGError",
    "DocumentLoadingError",
    "UnsupportedFormatError",
    "NormalizationError",
    "ChunkingError",
    "PipelineExecutionError",
]
