"""Unit tests for Cache-Augmented Generation (CAG) subsystem."""

import time
import pytest

from xeren.core.data_holding import PermittedDataHoldingVault
from xeren.core.vault import UserVault
from xeren.rag.cag.engine import CAGRetrievalEngine
from xeren.rag.cag.types import CachePolicy


def test_cag_put_and_get_hit() -> None:
    engine = CAGRetrievalEngine()
    query = "How do I configure PostgreSQL connection pool?"
    context = "Use postgresql://localhost:5432 with max_connections=20."

    engine.put(query=query, context_text=context)

    entry = engine.get(query)
    assert entry is not None
    assert entry.context_text == context
    assert entry.access_count == 2  # 1 on put, 1 on get
    assert engine.stats.hits == 1
    assert engine.stats.misses == 0
    assert engine.stats.hit_rate == 1.0


def test_cag_cache_miss() -> None:
    engine = CAGRetrievalEngine()
    entry = engine.get("Unknown non-existent query")
    assert entry is None
    assert engine.stats.hits == 0
    assert engine.stats.misses == 1
    assert engine.stats.hit_rate == 0.0


def test_cag_ttl_expiration() -> None:
    current_time = 1000.0

    def mock_time() -> float:
        return current_time

    engine = CAGRetrievalEngine(default_ttl_seconds=60.0, time_provider=mock_time)
    engine.put(query="Temporary query", context_text="Temp data", ttl_seconds=30.0)

    # Within TTL
    current_time = 1010.0
    assert engine.get("Temporary query") is not None

    # Surpass TTL
    current_time = 1040.0
    assert engine.get("Temporary query") is None
    assert engine.stats.evictions == 1


def test_cag_lru_eviction() -> None:
    engine = CAGRetrievalEngine(max_entries=2)

    engine.put(query="q1", context_text="c1")
    engine.put(query="q2", context_text="c2")

    # Access q1 to make q2 the least recently used
    _ = engine.get("q1")

    # Put q3, which should evict q2
    engine.put(query="q3", context_text="c3")

    assert engine.get("q1") is not None
    assert engine.get("q3") is not None
    assert engine.get("q2") is None
    assert engine.stats.evictions == 1


def test_cag_invalidation_by_content_hash() -> None:
    engine = CAGRetrievalEngine()
    doc_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    engine.put(
        query="Explain API security",
        context_text="API keys must be encrypted.",
        content_hashes=[doc_hash],
    )

    assert engine.get("Explain API security") is not None

    # Invalidate by hash
    invalidated = engine.invalidate_by_hash(doc_hash)
    assert invalidated == 1
    assert engine.get("Explain API security") is None


def test_cag_invalidation_by_source() -> None:
    engine = CAGRetrievalEngine()
    source_file = "d:/Xeren/docs/architecture.md"

    engine.put(
        query="System design overview",
        context_text="Microkernel architecture.",
        source_identifiers=[source_file],
    )

    assert engine.get("System design overview") is not None

    invalidated = engine.invalidate_by_source(source_file)
    assert invalidated == 1
    assert engine.get("System design overview") is None


def test_cag_sync_with_data_vault(tmp_path) -> None:
    # Setup temporary permitted directory
    vault_dir = tmp_path / "permitted_vault"
    vault_dir.mkdir()
    doc_file = vault_dir / "app_spec.txt"
    doc_file.write_text("Version 1.0 Specification", encoding="utf-8")

    vault_db = tmp_path / "test_vault.db"
    user_vault = UserVault(db_path=vault_db)
    user_vault.grant_directory(vault_dir)

    holding_vault = PermittedDataHoldingVault(vault=user_vault)
    held_item = holding_vault.hold_device_file(file_path=doc_file)
    assert held_item is not None

    cag = CAGRetrievalEngine()
    cag.put(
        query="What is the app version?",
        context_text="Version 1.0 Specification",
        content_hashes=[held_item.content_hash],
        source_identifiers=[held_item.source_identifier],
    )

    # Cache hit before file modification
    assert cag.get("What is the app version?") is not None

    # Modify file content on disk and update holding vault
    doc_file.write_text("Version 2.0 Specification", encoding="utf-8")
    updated_item = holding_vault.hold_device_file(file_path=doc_file)
    assert updated_item is not None
    assert updated_item.content_hash != held_item.content_hash

    # Sync CAG with Data Holding Vault: stale cached entry must be purged
    purged = cag.sync_with_data_vault(holding_vault)
    assert purged == 1
    assert cag.get("What is the app version?") is None


def test_cag_prewarm() -> None:
    engine = CAGRetrievalEngine()
    count = engine.prewarm([
        {"query": "Guideline A", "context_text": "Always write tests."},
        {"query": "Guideline B", "context_text": "Adhere to PEP 8."},
    ])
    assert count == 2
    assert engine.get("Guideline A") is not None
    assert engine.get("Guideline B") is not None
