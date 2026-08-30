"""Sparse keyword/lexical retriever supporting BM25-style relevance scoring."""

import math
import re
from typing import Callable, Dict, List, Optional, Set

from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.base import BaseRetriever
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult


class KeywordRetriever(BaseRetriever):
    """Lexical keyword retriever implementing BM25 term weighting."""

    def __init__(
        self,
        chunks_provider: Callable[[], List[DocumentChunk]],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.chunks_provider = chunks_provider
        self.k1 = k1
        self.b = b

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        if not query or not query.strip():
            return []

        chunks = self.chunks_provider()
        if not chunks:
            return []

        # Filter candidate chunks
        candidate_chunks = [
            c for c in chunks if not filter or filter.matches(c.metadata)
        ]
        if not candidate_chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Calculate document lengths and token frequencies
        doc_tokens_list: List[List[str]] = [self._tokenize(c.content) for c in candidate_chunks]
        doc_lengths = [len(tokens) for tokens in doc_tokens_list]
        avg_doc_len = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0

        # Calculate document frequency (DF) for query tokens
        num_docs = len(candidate_chunks)
        df: Dict[str, int] = {}
        for q_tok in set(query_tokens):
            df[q_tok] = sum(1 for tokens in doc_tokens_list if q_tok in tokens)

        # Compute BM25 scores
        scored_results: List[SearchResult] = []
        for idx, chunk in enumerate(candidate_chunks):
            tokens = doc_tokens_list[idx]
            doc_len = doc_lengths[idx]
            token_counts: Dict[str, int] = {}
            for t in tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            score = 0.0
            for q_tok in query_tokens:
                if q_tok not in token_counts:
                    continue
                tf = token_counts[q_tok]
                n_docs_with_tok = df.get(q_tok, 0)
                idf = math.log(1.0 + (num_docs - n_docs_with_tok + 0.5) / (n_docs_with_tok + 0.5))
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avg_doc_len))
                score += idf * (numerator / denominator)

            if score > 0.0:
                scored_results.append(
                    SearchResult(
                        chunk=chunk,
                        score=score,
                        retrieval_type="sparse",
                    )
                )

        scored_results.sort(key=lambda x: x.score, reverse=True)
        return scored_results[:top_k]
