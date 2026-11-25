"""Tests for PostgresConnectionManager and PostgresExperienceStore."""

import pytest
from xeren.db.postgres import PostgresConnectionManager
from xeren.plugins.experience.schemas import ExperienceItem
from xeren.plugins.experience.stores.postgres import PostgresExperienceStore


def test_postgres_manager_instantiation():
    """Verify PostgresConnectionManager initializes cleanly without throwing exceptions."""
    mgr = PostgresConnectionManager(default_uri="postgresql://user:pass@localhost:5432/testdb")
    status = mgr.get_status()
    assert "connected" in status
    assert "latency_ms" in status
    assert status["masked_uri"] == "postgresql://user:••••••••@localhost:5432/testdb"


def test_postgres_manager_verify_empty():
    """Verify PostgresConnectionManager handles empty URI gracefully."""
    mgr = PostgresConnectionManager(default_uri="")
    res = mgr.verify_connection(uri="")
    assert res["connected"] is False
    assert res["mode"] == "unconfigured"


def test_postgres_experience_store_crud():
    """Verify PostgresExperienceStore in test/in-memory environment supports complete CRUD."""
    store = PostgresExperienceStore(connection_uri="sqlite:///:memory:", auto_create_tables=True)

    item = ExperienceItem(
        task="Optimize SQL query for Postgres",
        selected_plugin="coding",
        action="index_optimization",
        outcome="index_created",
        success=True,
        tags=["postgres", "sql"],
    )

    # 1. Add
    item_id = store.add(item)
    assert item_id == item.id

    # 2. Get
    fetched = store.get(item_id)
    assert fetched is not None
    assert fetched.task == "Optimize SQL query for Postgres"
    assert fetched.selected_plugin == "coding"

    # 3. Get by fingerprint
    by_fp = store.get_by_fingerprint(fetched.content_fingerprint)
    assert by_fp is not None
    assert by_fp.id == item_id

    # 4. Search
    search_res = store.search(query="Optimize", filters={"selected_plugin": "coding"})
    assert len(search_res) == 1
    assert search_res[0].id == item_id

    # 5. Update
    up_ok = store.update(item_id, {"confidence": 0.95, "lesson": "Use indexes for queries"})
    assert up_ok is True
    updated = store.get(item_id)
    assert updated is not None
    assert updated.confidence == 0.95
    assert updated.lesson == "Use indexes for queries"

    # 6. Count and Clear
    assert store.count() == 1
    assert store.count(filters={"selected_plugin": "coding"}) == 1
    assert store.count(filters={"selected_plugin": "nonexistent"}) == 0

    # 7. Delete
    deleted = store.delete(item_id)
    assert deleted is True
    assert store.get(item_id) is None
    assert store.count() == 0
