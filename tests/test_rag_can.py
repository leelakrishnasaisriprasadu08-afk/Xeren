"""Tests for RAG CAN modules (BM25 Worker, Vector Worker, and Policy Gate Verifier)."""

import json
import sqlite3
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.rag.bm25_worker import BM25LexicalWorker, execute_search, tokenize_text
from src.rag.vector_worker import DenseVectorWorker
from src.rag.verifier import EvidenceVerification, parse_evidence_verification


def test_tokenize_text():
    text = "def calculate_sum(a, b): return a + b"
    tokens = tokenize_text(text)
    assert "calculate_sum" in tokens
    assert "def" in tokens
    assert "return" in tokens


def test_bm25_worker_search(tmp_path):
    # Setup temporary SQLite database
    db_file = tmp_path / "test_xeren.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        """
        CREATE TABLE code_chunks (
            id TEXT PRIMARY KEY,
            filepath TEXT,
            content TEXT,
            metadata TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO code_chunks VALUES (?, ?, ?, ?)",
        ("chunk_1", "src/auth.py", "def authenticate_user(token: str): pass", "{}"),
    )
    conn.execute(
        "INSERT INTO code_chunks VALUES (?, ?, ?, ?)",
        ("chunk_2", "src/database.py", "def query_database(query_str: str): pass", "{}"),
    )
    conn.execute(
        "INSERT INTO code_chunks VALUES (?, ?, ?, ?)",
        ("chunk_3", "src/models.py", "class SystemConfig: pass", "{}"),
    )
    conn.commit()
    conn.close()

    worker = BM25LexicalWorker(db_path=db_file)
    results = worker.search("authenticate token")

    assert len(results) > 0
    assert results[0]["id"] == "chunk_1"
    assert "src/auth.py" in results[0]["filepath"]
    assert results[0]["score"] > 0


def test_evidence_verification_pass():
    data = {
        "IS_RELEVANT": True,
        "IS_SUPPORTED": True,
        "HAS_PERMISSION": True,
        "VERDICT": "PASS",
        "correction_hint": "",
    }
    ev = parse_evidence_verification(data)
    assert ev.IS_RELEVANT is True
    assert ev.VERDICT == "PASS"


def test_evidence_verification_json_string():
    json_text = json.dumps({
        "IS_RELEVANT": False,
        "IS_SUPPORTED": False,
        "HAS_PERMISSION": True,
        "VERDICT": "REJECT_AND_RETRY",
        "correction_hint": "Please query for exact method signature.",
    })
    ev = parse_evidence_verification(json_text)
    assert ev.VERDICT == "REJECT_AND_RETRY"
    assert "exact method signature" in ev.correction_hint


def test_evidence_verification_fenced_markdown():
    fenced_text = """Here is the policy evaluation:
```json
{
    "IS_RELEVANT": true,
    "IS_SUPPORTED": false,
    "HAS_PERMISSION": false,
    "VERDICT": "ABSTAIN",
    "correction_hint": "Access denied to private repository."
}
```
"""
    ev = parse_evidence_verification(fenced_text)
    assert ev.VERDICT == "ABSTAIN"
    assert ev.HAS_PERMISSION is False


def test_evidence_verification_invalid_verdict():
    with pytest.raises(Exception):
        parse_evidence_verification({
            "IS_RELEVANT": True,
            "IS_SUPPORTED": True,
            "HAS_PERMISSION": True,
            "VERDICT": "INVALID_VERDICT_VALUE",
            "correction_hint": "",
        })


def test_dense_vector_worker_search(monkeypatch, tmp_path):
    worker = DenseVectorWorker(storage_path=tmp_path / "qdrant_test")

    # Mock SentenceTransformer model
    class MockModel:
        def encode(self, query):
            class Arr:
                def tolist(self):
                    return [0.1] * 384
            return Arr()

    # Mock Qdrant Point and search response
    class MockPoint:
        id = "vector_chunk_1"
        score = 0.92
        payload = {
            "filepath": "src/rag/vector_worker.py",
            "content": "class DenseVectorWorker: pass",
            "metadata": {"source": "codebase"}
        }

    class MockQueryResult:
        points = [MockPoint()]

    class MockClient:
        def get_collections(self):
            class CollResp:
                collections = []
            return CollResp()

        def create_collection(self, **kwargs):
            pass

        def query_points(self, **kwargs):
            return MockQueryResult()

    monkeypatch.setattr(worker, "_model", MockModel())
    monkeypatch.setattr(worker, "_client", MockClient())

    results = worker.search("Dense vector search architecture", limit=3)
    assert len(results) == 1
    assert results[0]["id"] == "vector_chunk_1"
    assert results[0]["score"] == 0.92
    assert "src/rag/vector_worker.py" in results[0]["filepath"]
    assert results[0]["match_type"] == "dense_semantic_vector"


