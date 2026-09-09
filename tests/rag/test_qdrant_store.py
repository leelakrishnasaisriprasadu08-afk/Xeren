"""Unit tests for QdrantVectorStore in Xeren RAG."""

from __future__ import annotations

import pytest

from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.stores.qdrant import QdrantVectorStore


class TestQdrantVectorStore:
    def test_qdrant_add_and_search(self):
        store = QdrantVectorStore(persist_path=":memory:")

        # Create two sample chunks
        chunk1 = DocumentChunk(
            chunk_id="chunk_ai_001",
            document_id="doc_ai",
            content="Local LLMs run completely on private hardware without sending data to external clouds.",
            chunk_index=0,
            total_chunks=1,
            character_count=85,
        )
        emb1 = EmbeddedChunk(
            chunk=chunk1,
            embedding=[0.1, 0.9, 0.2, 0.0] * 96,  # 384-dim vector
            embedding_model="local-sentence-transformer",
        )

        chunk2 = DocumentChunk(
            chunk_id="chunk_crypto_002",
            document_id="doc_crypto",
            content="AES-256-GCM provides authenticated encryption with integrity tags for high sensitivity data.",
            chunk_index=0,
            total_chunks=1,
            character_count=90,
        )
        emb2 = EmbeddedChunk(
            chunk=chunk2,
            embedding=[0.8, 0.1, 0.1, 0.7] * 96,  # 384-dim vector
            embedding_model="local-sentence-transformer",
        )

        inserted = store.add_chunks([emb1, emb2])
        assert len(inserted) == 2
        assert store.count() == 2

        # Search with vector close to emb1
        query_vector = [0.1, 0.85, 0.25, 0.0] * 96
        results = store.similarity_search(query_vector=query_vector, top_k=1)
        assert len(results) == 1
        assert results[0].chunk.chunk_id == "chunk_ai_001"
        assert "Local LLMs" in results[0].chunk.content
        assert results[0].score > 0.90

    def test_qdrant_delete_and_clear(self):
        store = QdrantVectorStore(persist_path=":memory:")

        chunk = DocumentChunk(
            chunk_id="test_del_1",
            document_id="doc_test",
            content="Test content to delete",
            chunk_index=0,
            total_chunks=1,
            character_count=22,
        )
        emb = EmbeddedChunk(
            chunk=chunk,
            embedding=[0.5] * 384,
            embedding_model="local-test",
        )

        store.add_chunks([emb])
        assert store.count() == 1

        deleted = store.delete(["test_del_1"])
        assert deleted == 1
        assert store.count() == 0

        # Test clear
        store.add_chunks([emb])
        assert store.count() == 1
        store.clear()
        assert store.count() == 0
