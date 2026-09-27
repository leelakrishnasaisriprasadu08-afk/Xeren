"""Lightweight local cross-feature reranker for Xeren RAG.

Evaluates joint query-chunk relevance without external dependencies using:
1. Query term coverage (token recall).
2. Exact phrase and n-gram sequence alignment.
3. Term proximity / span compactness.
4. Structural header and metadata relevance.
5. First-stage retrieval prior fusion.
"""

import re
from typing import List, Optional

from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.types import SearchResult


class LocalReranker(BaseReranker):
    """Local heuristic cross-feature reranker producing calibrated [0.0, 1.0] relevance scores."""

    def __init__(
        self,
        coverage_weight: float = 0.40,
        phrase_weight: float = 0.30,
        proximity_weight: float = 0.20,
        header_weight: float = 0.10,
        retrieval_prior_weight: float = 0.30,
    ) -> None:
        self.coverage_weight = coverage_weight
        self.phrase_weight = phrase_weight
        self.proximity_weight = proximity_weight
        self.header_weight = header_weight
        self.retrieval_prior_weight = retrieval_prior_weight

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _compute_phrase_score(self, query_tokens: List[str], doc_tokens: List[str], raw_query: str, doc_text: str) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0

        # Exact contiguous match of the full query
        clean_query = " ".join(query_tokens)
        clean_doc = " ".join(doc_tokens)
        if len(query_tokens) > 1 and clean_query in clean_doc:
            return 1.0

        if len(query_tokens) == 1:
            return 1.0 if query_tokens[0] in doc_tokens else 0.0

        # Bigram overlap
        query_bigrams = set(zip(query_tokens[:-1], query_tokens[1:]))
        doc_bigrams = set(zip(doc_tokens[:-1], doc_tokens[1:]))
        if not query_bigrams:
            return 0.0

        matched_bigrams = len(query_bigrams.intersection(doc_bigrams))
        return matched_bigrams / len(query_bigrams)

    def _compute_proximity_score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        unique_q = list(set(query_tokens))
        if len(unique_q) <= 1:
            return 1.0 if any(q in doc_tokens for q in unique_q) else 0.0

        # Find first positions of each matched query token
        positions = []
        for q in unique_q:
            if q in doc_tokens:
                positions.append(doc_tokens.index(q))

        if len(positions) < 2:
            return 0.5 if len(positions) == 1 else 0.0

        min_pos = min(positions)
        max_pos = max(positions)
        span_len = max_pos - min_pos + 1
        ideal_span = len(positions)

        # Proximity score decay based on span length
        return min(1.0, max(0.0, ideal_span / max(ideal_span, span_len)))

    def _compute_header_score(self, query_tokens: List[str], metadata: dict) -> float:
        if not query_tokens or not metadata:
            return 0.0

        header_text = " ".join([
            str(metadata.get("title", "")),
            str(metadata.get("header_path", "")),
            str(metadata.get("current_header", "")),
        ]).lower()

        if not header_text.strip():
            return 0.0

        header_tokens = set(self._tokenize(header_text))
        if not header_tokens:
            return 0.0

        unique_q = set(query_tokens)
        matched = len(unique_q.intersection(header_tokens))
        return matched / len(unique_q)

    def _score_candidate(self, query: str, query_tokens: List[str], result: SearchResult) -> float:
        doc_text = result.chunk.content
        doc_tokens = self._tokenize(doc_text)

        if not query_tokens or not doc_tokens:
            return 0.0

        unique_q = set(query_tokens)
        doc_token_set = set(doc_tokens)

        # 1. Term coverage
        coverage_score = len(unique_q.intersection(doc_token_set)) / len(unique_q)

        # 2. Phrase / bigram score
        phrase_score = self._compute_phrase_score(query_tokens, doc_tokens, query, doc_text)

        # 3. Proximity score
        proximity_score = self._compute_proximity_score(query_tokens, doc_tokens)

        # 4. Header / structural score
        header_score = self._compute_header_score(query_tokens, result.chunk.metadata)

        # Cross score combination
        cross_score = (
            self.coverage_weight * coverage_score
            + self.phrase_weight * phrase_score
            + self.proximity_weight * proximity_score
            + self.header_weight * header_score
        )

        # Normalize prior retrieval score to [0.0, 1.0]
        initial_score = min(1.0, max(0.0, result.score))

        # Blend cross score with first-stage prior
        final_score = (
            (1.0 - self.retrieval_prior_weight) * cross_score
            + self.retrieval_prior_weight * initial_score
        )

        return min(1.0, max(0.0, final_score))

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        if not results:
            return []

        if not query or not query.strip():
            return results[:top_n] if top_n is not None else results

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return results[:top_n] if top_n is not None else results

        reranked = []
        for r in results:
            score = self._score_candidate(query, query_tokens, r)
            reranked.append(
                SearchResult(
                    chunk=r.chunk,
                    score=round(score, 4),
                    retrieval_type="reranked",
                    vector=r.vector,
                )
            )

        reranked.sort(key=lambda x: x.score, reverse=True)
        if top_n is not None:
            return reranked[:top_n]
        return reranked
