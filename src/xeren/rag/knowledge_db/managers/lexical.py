"""LexicalIndexManager managing SQLite BM25 term frequencies and inverted search."""

from collections import defaultdict
import math
import re
from typing import Dict, List, Optional, Set, Tuple
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class LexicalIndexManager:
    """Manages sparse token indexing and BM25 relevance scoring in SQLite."""

    def __init__(self, connection_mgr: ConnectionManager, k1: float = 1.5, b: float = 0.75) -> None:
        self.conn_mgr = connection_mgr
        self.k1 = k1
        self.b = b

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Normalize and tokenize text into keywords and code identifiers."""
        if not text:
            return []
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        results: List[str] = []
        for t in tokens:
            if len(t) > 1:
                results.append(t)
                parts = t.split("_")
                if len(parts) > 1:
                    results.extend(p for p in parts if len(p) > 1)
        return results

    def index_chunk_terms(self, chunk_id: str, content: str) -> None:
        """Tokenize content and record term frequencies in lexical_index."""
        tokens = self.tokenize(content)
        if not tokens:
            return

        total_tokens = len(tokens)
        counts: Dict[str, int] = defaultdict(int)
        for t in tokens:
            counts[t] += 1

        rows = [
            (chunk_id, term, round(count / float(total_tokens), 4), 1)
            for term, count in counts.items()
        ]

        with self.conn_mgr.transaction() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO lexical_index (
                    chunk_id, term, term_frequency, document_frequency
                ) VALUES (?, ?, ?, ?);
                """,
                rows,
            )

    def search_lexical(
        self,
        query: str,
        top_k: int = 5,
        candidate_chunk_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Compute sparse term scores for query tokens."""
        tokens = self.tokenize(query)
        if not tokens:
            return []

        conn = self.conn_mgr.get_connection()
        qmarks = ",".join("?" for _ in tokens)
        cursor = conn.execute(
            f"SELECT chunk_id, term, term_frequency FROM lexical_index WHERE term IN ({qmarks});",
            tokens,
        )

        scores: Dict[str, float] = defaultdict(float)
        for row in cursor.fetchall():
            cid = row["chunk_id"]
            if candidate_chunk_ids is not None and cid not in candidate_chunk_ids:
                continue
            tf = row["term_frequency"]
            # Simple TF-based relevance weighting
            scores[cid] += float(tf) * 1.5

        if not scores:
            return []

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def delete_chunk_terms(self, chunk_ids: List[str]) -> int:
        """Remove terms associated with deleted chunks."""
        if not chunk_ids:
            return 0
        with self.conn_mgr.transaction() as conn:
            qmarks = ",".join("?" for _ in chunk_ids)
            conn.execute(
                f"DELETE FROM lexical_index WHERE chunk_id IN ({qmarks});",
                chunk_ids,
            )
        return len(chunk_ids)
