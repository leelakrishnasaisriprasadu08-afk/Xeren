"""Tests for InMemoryExperienceStore and MongoExperienceStore adapters."""

import pytest

from xeren.plugins.experience.schemas import ExperienceItem
from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.stores.memory import InMemoryExperienceStore
from xeren.plugins.experience.stores.mongo import MongoExperienceStore


@pytest.fixture
def memory_store():
    return InMemoryExperienceStore()


def test_memory_store_add_get_delete(memory_store):
    """Verify InMemoryExperienceStore basic CRUD cycle."""
    item = ExperienceItem(
        task="Test task",
        selected_plugin="coding",
        action="syntax_check",
        outcome="valid",
        success=True,
    )
    item_id = memory_store.add(item)
    assert item_id == item.id

    fetched = memory_store.get(item_id)
    assert fetched is not None
    assert fetched.task == "Test task"
    assert fetched.content_fingerprint != ""

    # Get by fingerprint
    by_fp = memory_store.get_by_fingerprint(fetched.content_fingerprint)
    assert by_fp is not None
    assert by_fp.id == item_id

    # Delete
    deleted = memory_store.delete(item_id)
    assert deleted is True
    assert memory_store.get(item_id) is None
    assert memory_store.get_by_fingerprint(fetched.content_fingerprint) is None


def test_memory_store_search_filters(memory_store):
    """Verify search filtering by text query, success, plugin, and tags."""
    item1 = ExperienceItem(
        task="Sort an array of integers",
        selected_plugin="coding",
        action="generate",
        success=True,
        tags=["algorithms", "sorting"],
    )
    item2 = ExperienceItem(
        task="Inspect sales spreadsheet",
        selected_plugin="data",
        action="inspect",
        success=True,
        tags=["spreadsheet"],
    )
    item3 = ExperienceItem(
        task="Delete production database",
        selected_plugin="data",
        action="delete",
        success=False,
        failure_reason="Permission denied",
    )

    memory_store.add(item1)
    memory_store.add(item2)
    memory_store.add(item3)

    assert memory_store.count() == 3

    # Query search
    res_query = memory_store.search(query="array sorting")
    assert len(res_query) == 1
    assert res_query[0].id == item1.id

    # Success filter
    res_success = memory_store.search(filters={"success": True})
    assert len(res_success) == 2

    # Plugin filter
    res_data = memory_store.search(filters={"selected_plugin": "data"})
    assert len(res_data) == 2

    # Tag filter
    res_tag = memory_store.search(filters={"tag": "spreadsheet"})
    assert len(res_tag) == 1
    assert res_tag[0].id == item2.id


def test_memory_store_update(memory_store):
    """Verify update modifies fields."""
    item = ExperienceItem(task="Initial task", confidence=0.5)
    memory_store.add(item)

    success = memory_store.update(item.id, {"confidence": 0.95, "lesson": "New lesson learned"})
    assert success is True

    updated = memory_store.get(item.id)
    assert updated is not None
    assert updated.confidence == 0.95
    assert updated.lesson == "New lesson learned"


def test_memory_store_clear(memory_store):
    """Verify clear empties the store."""
    memory_store.add(ExperienceItem(task="Task A"))
    memory_store.add(ExperienceItem(task="Task B"))
    assert memory_store.count() == 2
    memory_store.clear()
    assert memory_store.count() == 0


@pytest.mark.asyncio
async def test_memory_store_async_methods(memory_store):
    """Verify asynchronous store methods."""
    item = ExperienceItem(task="Async task", success=True)
    item_id = await memory_store.aadd(item)
    assert item_id == item.id

    fetched = await memory_store.aget(item_id)
    assert fetched is not None

    count = await memory_store.acount()
    assert count == 1

    search_res = await memory_store.asearch(query="Async")
    assert len(search_res) == 1

    up_res = await memory_store.aupdate(item_id, {"confidence": 0.88})
    assert up_res is True

    del_res = await memory_store.adelete(item_id)
    assert del_res is True

    await memory_store.aclear()
    assert await memory_store.acount() == 0


def test_mongo_store_interface_and_error_handling():
    """Verify MongoExperienceStore inherits BaseExperienceStore and safely reports connection requirements."""
    store = MongoExperienceStore(
        connection_uri="mongodb://localhost:27017",
        database_name="xeren_test",
        auto_connect=False,
    )
    assert isinstance(store, BaseExperienceStore)
    assert store.connection_uri == "mongodb://localhost:27017"
    assert store.database_name == "xeren_test"

    # When pymongo is not connected or installed, calling operations gives clean RuntimeError
    if not store.is_connected:
        with pytest.raises(RuntimeError) as exc_info:
            store.get("some_id")
        assert "MongoExperienceStore is not connected" in str(exc_info.value)
