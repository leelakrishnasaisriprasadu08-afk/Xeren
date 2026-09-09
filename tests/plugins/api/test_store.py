"""Unit tests for persistent API key storage interfaces (In-Memory and MongoDB)."""

from unittest.mock import MagicMock
import pytest

from xeren.plugins.api.schemas import ApiKeyMetadata
from xeren.plugins.api.tools.store import InMemoryApiKeyStore, MongoApiKeyStore


def test_in_memory_store_crud():
    """Verify in-memory key store CRUD lifecycle."""
    store = InMemoryApiKeyStore()
    key1 = ApiKeyMetadata(
        key_id="k1",
        name="Key One",
        prefix="xrn_live_k1...",
        key_hash="hash1",
        salt="salt1",
        scopes=["research"],
    )
    key2 = ApiKeyMetadata(
        key_id="k2",
        name="Key Two",
        prefix="xrn_live_k2...",
        key_hash="hash2",
        salt="salt2",
        scopes=["data"],
    )

    # Save
    store.save_key(key1)
    store.save_key(key2)

    # Retrieve by ID
    assert store.get_key("k1") == key1
    assert store.get_key("missing") is None

    # Retrieve by Hash
    assert store.get_key_by_hash("hash2") == key2
    assert store.get_key_by_hash("missing_hash") is None

    # List
    all_keys = store.list_keys(include_revoked=True)
    assert len(all_keys) == 2

    # Update
    key1.name = "Key One Updated"
    store.update_key(key1)
    updated_k1 = store.get_key("k1")
    assert updated_k1 is not None
    assert updated_k1.name == "Key One Updated"

    # Delete
    deleted = store.delete_key("k1")
    assert deleted is True
    assert store.get_key("k1") is None
    assert store.get_key_by_hash("hash1") is None
    assert store.delete_key("k1") is False


def test_mongo_store_not_connected():
    """Verify MongoApiKeyStore raises clear RuntimeError if initialized without collection or pymongo."""
    store = MongoApiKeyStore(collection=None, uri=None)
    key = ApiKeyMetadata(
        key_id="k1",
        name="Key",
        prefix="xrn_live_...",
        key_hash="h",
        salt="s",
    )
    with pytest.raises(RuntimeError) as exc_info:
        store.save_key(key)
    assert "not connected" in str(exc_info.value).lower()


def test_mongo_store_with_mock_collection():
    """Verify MongoApiKeyStore properly delegates to MongoDB collection API."""
    mock_collection = MagicMock()
    store = MongoApiKeyStore(collection=mock_collection)

    key = ApiKeyMetadata(
        key_id="k1",
        name="Test Mongo Key",
        prefix="xrn_live_123...",
        key_hash="h123",
        salt="s123",
    )

    # Save key
    store.save_key(key)
    mock_collection.replace_one.assert_called_once()

    # Get key
    mock_collection.find_one.return_value = key.model_dump(mode="python")
    retrieved = store.get_key("k1")
    assert retrieved is not None
    assert retrieved.name == "Test Mongo Key"

    # Delete key
    mock_collection.delete_one.return_value = MagicMock(deleted_count=1)
    assert store.delete_key("k1") is True
