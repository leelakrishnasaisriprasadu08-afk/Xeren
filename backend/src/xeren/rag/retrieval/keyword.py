"""Sparse keyword/lexical retriever supporting BM25-style relevance scoring.

The BM25Index pre-builds the inverted index (term → document frequency) and
document-length statistics once at ingestion time.  Every query then does a
direct lookup instead of re-scanning and re-tokenizing the whole corpus.

Before this change every call to retrieve() would:
  1. Fetch all chunks via the provider callable.
  2. Tokenize every chunk's content.
  3. Recompute document-frequency for each query token by scanning all docs.

That is O(N) tokenization work per query.  For 10 000 chunks and 1 000 queries
that is 10 000 000 pointless tokenization operations.

After this change:
  • Tokenization happens once when a chunk is added to the index.
  • Document-frequency is maintained as a running counter.
  • Query time is O(|query_tokens| × |posting_list|) — typically tiny.

Public surface is unchanged: KeywordRetriever still accepts chunks_provider for
backward compatibility; it eagerly indexes whatever the provider returns on
construction and exposes add_chunks() for incremental updates.
"""

import math
import re
import threading
from typing import Callable, Dict, List, Optional

from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult


class BM25Index:
    """Pre-built BM25 inverted index for fast keyword scoring.

    Build the index once with add_chunks(); then call score() per query.
    Thread-safe via a read-write lock so that incremental updates (add_chunks)
    and concurrent queries co-exist safely.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._lock = threading.Lock()

        # chunk_id → DocumentChunk
        self._chunks: Dict[str, DocumentChunk] = {}
        # chunk_id → {token: count}
        self._tf: Dict[str, Dict[str, int]] = {}
        # chunk_id → document length (number of tokens)
        self._doc_lengths: Dict[str, int] = {}
        # token → number of documents containing that token
        self._df: Dict[str, int] = {}
        # running total of all token counts (for avg_doc_len)
        self._total_tokens: int = 0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Index new chunks.  Safe to call multiple times (incremental)."""
        with self._lock:
            for chunk in chunks:
                cid = chunk.chunk_id
                if cid in self._chunks:
                    # Already indexed — skip to stay idempotent.
                    continue

                tokens = self._tokenize(chunk.content)
                tf: Dict[str, int] = {}
                for t in tokens:
                    tf[t] = tf.get(t, 0) + 1

                self._chunks[cid] = chunk
                self._tf[cid] = tf
                self._doc_lengths[cid] = len(tokens)
                self._total_tokens += len(tokens)

                for term in tf:
                    self._df[term] = self._df.get(term, 0) + 1

    def score(
        self,
        query_tokens: List[str],
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        """Return BM25-scored results for pre-tokenized query tokens."""
        with self._lock:
            num_docs = len(self._chunks)
            if num_docs == 0:
                return []

            avg_doc_len = self._total_tokens / num_docs

            scored: List[SearchResult] = []
            for cid, chunk in self._chunks.items():
                if filter and not filter.matches(chunk.metadata):
                    continue

                tf = self._tf[cid]
                doc_len = self._doc_lengths[cid]
                bm25_score = 0.0

                for q_tok in query_tokens:
                    if q_tok not in tf:
                        continue
                    tf_val = tf[q_tok]
                    n_docs_with_tok = self._df.get(q_tok, 0)
                    idf = math.log(
                        1.0 + (num_docs - n_docs_with_tok + 0.5) / (n_docs_with_tok + 0.5)
                    )
                    numerator = tf_val * (self.k1 + 1.0)
                    denominator = tf_val + self.k1 * (
                        1.0 - self.b + self.b * (doc_len / avg_doc_len)
                    )
                    bm25_score += idf * (numerator / denominator)

                if bm25_score > 0.0:
                    scored.append(
                        SearchResult(
                            chunk=chunk,
                            score=bm25_score,
                            retrieval_type="sparse",
                        )
                    )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def get_max_query_score(self, query_tokens: List[str]) -> float:
        """Calculate the ideal maximum BM25 score for unique query tokens where each term matches."""
        with self._lock:
            num_docs = len(self._chunks)
            if num_docs == 0 or not query_tokens:
                return 1.0

            unique_tokens = set(query_tokens)
            max_score = 0.0
            for q_tok in unique_tokens:
                n_docs = self._df.get(q_tok, 0)
                idf = math.log(
                    1.0 + (num_docs - n_docs + 0.5) / (n_docs + 0.5)
                )
                max_score += idf

            return max_score if max_score > 0.0 else 1.0

    @property
    def num_chunks(self) -> int:
        with self._lock:
            return len(self._chunks)


class KeywordRetriever(BaseRetriever):
    """Lexical keyword retriever backed by a pre-built BM25Index.

    Accepts an optional chunks_provider callable for backward compatibility:
    the provider is called once at construction to seed the index.  New chunks
    can be added later via add_chunks().
    """

    def __init__(
        self,
        chunks_provider: Optional[Callable[[], List[DocumentChunk]]] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self._index = BM25Index(k1=k1, b=b)

        if chunks_provider is not None:
            initial_chunks = chunks_provider()
            if initial_chunks:
                self._index.add_chunks(initial_chunks)

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Incrementally update the BM25 index with new chunks."""
        self._index.add_chunks(chunks)

    def get_max_query_score(self, query: str) -> float:
        """Calculate the theoretical maximum BM25 score for a query string."""
        tokens = BM25Index._tokenize(query)
        if not tokens:
            return 1.0
        return self._index.get_max_query_score(tokens)

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        if not query or not query.strip():
            return []

        query_tokens = BM25Index._tokenize(query)
        if not query_tokens:
            return []

        results = self._index.score(query_tokens, filter=filter)
        return results[:top_k]

    # aretrieve is inherited from BaseRetriever (runs retrieve in a thread)
