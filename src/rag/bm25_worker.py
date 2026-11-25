"""BM25 Lexical Search Worker MCP Server.

Provides exact-match keyword search against SQLite code chunks using BM25Okapi.
"""

from __future__ import annotations

import math
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try importing FastMCP from official MCP SDK, provide fallback mock if unavailable
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    class FastMCP:  # type: ignore[no-redef]
        """Fallback FastMCP implementation when mcp package is pending installation."""
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools: Dict[str, Any] = {}

        def tool(self, name: Optional[str] = None):
            def decorator(func):
                tool_name = name or func.__name__
                self.tools[tool_name] = func
                return func
            return decorator

        def run(self) -> None:
            print(f"[{self.name}] Running in standalone fallback mode.")

# Try importing BM25Okapi from rank_bm25, provide pure-Python implementation if unavailable
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    class BM25Okapi:  # type: ignore[no-redef]
        """Self-contained BM25Okapi implementation fallback."""
        def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75, epsilon: float = 0.25) -> None:
            self.corpus_size = len(corpus)
            self.avgdl = sum(float(len(doc)) for doc in corpus) / self.corpus_size if self.corpus_size > 0 else 0.0
            self.corpus = corpus
            self.k1 = k1
            self.b = b
            self.epsilon = epsilon
            self.doc_freqs: List[Dict[str, int]] = []
            self.idf: Dict[str, float] = {}
            self.doc_len: List[int] = []
            nd: Dict[str, int] = {}
            for document in corpus:
                self.doc_len.append(len(document))
                frequencies: Dict[str, int] = {}
                for word in document:
                    frequencies[word] = frequencies.get(word, 0) + 1
                self.doc_freqs.append(frequencies)
                for word in frequencies:
                    nd[word] = nd.get(word, 0) + 1

            idf_sum = 0.0
            negative_idfs = []
            for word, freq in nd.items():
                idf_val = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)
                self.idf[word] = idf_val
                idf_sum += idf_val
                if idf_val < 0:
                    negative_idfs.append(word)

            average_idf = idf_sum / len(self.idf) if self.idf else 0.0
            eps = self.epsilon * average_idf
            for word in negative_idfs:
                self.idf[word] = eps

        def get_scores(self, query: List[str]) -> List[float]:
            scores = [0.0] * self.corpus_size
            if not self.corpus_size or not self.avgdl:
                return scores
            for q in query:
                q_idf = self.idf.get(q, 0.0)
                for doc_idx in range(self.corpus_size):
                    doc_freq = self.doc_freqs[doc_idx].get(q, 0)
                    if doc_freq:
                        num = doc_freq * (self.k1 + 1.0)
                        denom = doc_freq + self.k1 * (1.0 - self.b + self.b * (self.doc_len[doc_idx] / self.avgdl))
                        scores[doc_idx] += q_idf * (num / denom)
            return scores


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = Path(os.getenv("XEREN_DB_PATH", str(PROJECT_ROOT / "data" / "xeren.db")))

# Initialize MCP server
mcp = FastMCP("BM25_Lexical_Search")


def tokenize_text(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric keywords, including sub-tokens from snake_case."""
    raw_tokens = re.findall(r"[A-Za-z0-9_]+", (text or "").lower())
    result = []
    for t in raw_tokens:
        result.append(t)
        if "_" in t:
            for sub in t.split("_"):
                if sub:
                    result.append(sub)
    return result



def ensure_code_chunks_table(conn: sqlite3.Connection) -> None:
    """Ensure code_chunks table exists in the database."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS code_chunks (
            id TEXT PRIMARY KEY,
            filepath TEXT,
            content TEXT,
            metadata TEXT
        )
        """
    )
    conn.commit()


class BM25LexicalWorker:
    """Handles BM25 tokenization and retrieval over the code_chunks database table."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Executes lexical BM25 search across code chunks."""
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            ensure_code_chunks_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT id, filepath, content, metadata FROM code_chunks")
            rows = cursor.fetchall()
            if not rows:
                return []

            corpus_docs = [dict(row) for row in rows]
            tokenized_corpus = [tokenize_text(doc.get("content", "")) for doc in corpus_docs]
            tokenized_query = tokenize_text(query)

            if not tokenized_query or not tokenized_corpus:
                return []

            bm25 = BM25Okapi(tokenized_corpus)
            scores = bm25.get_scores(tokenized_query)

            # Rank documents by BM25 score descending
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

            results: List[Dict[str, Any]] = []
            for idx in ranked_indices[:top_k]:
                score = float(scores[idx])
                if score <= 0.0 and len(results) > 0:
                    continue  # Stop if no positive keyword overlap remains
                doc = corpus_docs[idx]
                results.append(
                    {
                        "id": str(doc.get("id", "")),
                        "filepath": str(doc.get("filepath", "")),
                        "content": str(doc.get("content", "")),
                        "metadata": doc.get("metadata"),
                        "score": round(score, 4),
                        "match_type": "bm25_exact_lexical",
                    }
                )
            return results
        finally:
            conn.close()


@mcp.tool()
def execute_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Execute exact-match lexical keyword search on SQLite code_chunks table using BM25Okapi.

    Args:
        query: Lexical search terms or code symbols to search for.
        top_k: Maximum number of matches to return (default: 5).

    Returns:
        List of matching code chunk dicts with content and BM25 scores.
    """
    worker = BM25LexicalWorker()
    return worker.search(query=query, top_k=top_k)


if __name__ == "__main__":
    mcp.run()
