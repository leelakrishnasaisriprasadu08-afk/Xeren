"""Data schema and models for Xeren Sovereign Pattern Database (RAG Pipeline Only).

Strict Security Mandate:
This database stores knowledge representations, semantic vectors, lexical tokens,
code AST patterns, and document hierarchies strictly for the RAG retrieval pipeline.
Personal user credentials, session tokens, passwords, and private vault records are
explicitly forbidden and rejected by validation guards.
"""

from enum import Enum
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class SecurityIsolationError(ValueError):
    """Raised when an attempt is made to ingest user credentials or private secrets into the RAG Pattern DB."""
    pass


class PatternType(str, Enum):
    """Types of complex patterns supported by the Xeren Sovereign Pattern DB."""

    DENSE_VECTOR = "dense_vector"        # Semantic dense float embeddings
    SPARSE_LEXICAL = "sparse_lexical"    # BM25 tokens, keyword frequencies, identifiers
    CODE_AST = "code_ast"                # Abstract Syntax Tree patterns (classes, functions, calls)
    HIERARCHICAL = "hierarchical"        # Parent-child document/section trees and breadcrumbs
    KNOWLEDGE_TRIPLE = "knowledge_triple"# Subject-Predicate-Object relations
    FACETED_METRIC = "faceted_metric"    # Faceted metadata attributes (language, source, domain)


# Regex patterns matching potential secret/credential keys or tokens to enforce strict isolation
FORBIDDEN_KEY_PATTERNS = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|secret[_-]?key|password|auth[_-]?token|session[_-]?id|private[_-]?key|jwt)"
)
JWT_PATTERN = re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}")


class PatternRecord(BaseModel):
    """A sovereign pattern entity stored in the Xeren Pattern DB."""

    pattern_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this pattern record",
    )
    chunk_id: str = Field(
        ...,
        description="Reference to the originating DocumentChunk ID",
    )
    document_id: str = Field(
        ...,
        description="Reference to the originating source Document ID",
    )
    pattern_type: PatternType = Field(
        ...,
        description="The category of pattern represented",
    )
    signature: str = Field(
        ...,
        description="Searchable pattern signature, token identifier, or AST symbol name",
    )
    features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted pattern features (e.g., AST node type, arguments, level, parent_id)",
    )
    vector: Optional[List[float]] = Field(
        default=None,
        description="Optional dense embedding vector values",
    )
    sparse_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional sparse term weights or frequencies",
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized content snippet or code block for RAG retrieval context",
    )
    created_at: float = Field(
        default_factory=lambda: time.time(),
        description="Unix timestamp of pattern registration",
    )
    security_verified: bool = Field(
        default=True,
        description="True indicates passing RAG sovereign isolation verification",
    )

    @model_validator(mode="after")
    def verify_rag_pipeline_isolation(self) -> "PatternRecord":
        """Strict guardrail: ensure no user private credentials or session tokens are stored."""
        # Check signature
        if FORBIDDEN_KEY_PATTERNS.search(self.signature):
            if JWT_PATTERN.search(self.signature) or any(
                term in self.signature.lower() for term in ("key", "token", "secret", "password")
            ):
                raise SecurityIsolationError(
                    f"Pattern signature matches prohibited credential pattern: {self.signature}"
                )

        # Check features keys & values
        for k, v in self.features.items():
            if FORBIDDEN_KEY_PATTERNS.search(k):
                raise SecurityIsolationError(
                    f"Prohibited user credential feature '{k}' detected in RAG pattern."
                )
            if isinstance(v, str) and JWT_PATTERN.search(v):
                raise SecurityIsolationError(
                    f"Detected live JWT/token in feature '{k}'. Strictly isolated to UserVault."
                )

        # Check payload keys & values
        for k, v in self.payload.items():
            if FORBIDDEN_KEY_PATTERNS.search(k):
                raise SecurityIsolationError(
                    f"Prohibited user credential key '{k}' detected in RAG pattern payload."
                )
            if isinstance(v, str) and (JWT_PATTERN.search(v) or "sk-proj-" in v):
                raise SecurityIsolationError(
                    "Detected credential structure in RAG pattern payload. Strictly isolated to UserVault."
                )

        return self



class PatternQuery(BaseModel):
    """Query parameters for searching the Xeren Sovereign Pattern DB."""

    query_text: Optional[str] = Field(default=None, description="Text for keyword / AST / lexical matching")
    query_vector: Optional[List[float]] = Field(default=None, description="Dense vector for semantic matching")
    pattern_types: Optional[List[PatternType]] = Field(
        default=None, description="Filter search by specific pattern types"
    )
    symbol_name: Optional[str] = Field(default=None, description="Target AST code symbol or function name")
    ast_node_type: Optional[str] = Field(default=None, description="AST node type (e.g. FunctionDef, ClassDef)")
    parent_chunk_id: Optional[str] = Field(default=None, description="Filter by parent chunk for hierarchical lookup")
    facets: Optional[Dict[str, Any]] = Field(default=None, description="Exact match faceted metadata filters")
    top_k: int = Field(default=5, ge=1, description="Number of results to retrieve")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Hybrid blend (1.0 = purely vector, 0.0 = purely lexical/symbolic)")


class PatternSearchResult(BaseModel):
    """Ranked search result returned by the Sovereign Pattern DB."""

    pattern: PatternRecord = Field(..., description="The matched pattern record")
    score: float = Field(..., description="Combined or individual match score (higher is better)")
    match_source: str = Field(..., description="Mechanism that matched: 'dense', 'ast', 'sparse', 'hierarchy', or 'hybrid'")
    explanation: Optional[str] = Field(default=None, description="Optional diagnostic explaining match score")
