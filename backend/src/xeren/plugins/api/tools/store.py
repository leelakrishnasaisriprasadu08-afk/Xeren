"""Persistent API key storage interfaces and adapters (In-Memory and MongoDB)."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
import threading
from typing import Any, Dict, List, Optional

from xeren.plugins.api.schemas import ApiKeyMetadata

logger = logging.getLogger("xeren.plugins.api.tools.store")


class BaseApiKeyStore(ABC):
    """Abstract interface defining operations for persistent API key metadata."""

    @abstractmethod
    def save_key(self, key_meta: ApiKeyMetadata) -> None:
        """Persist a new API key metadata record."""
        pass

    @abstractmethod
    def get_key(self, key_id: str) -> Optional[ApiKeyMetadata]:
        """Retrieve an API key metadata record by its key_id."""
        pass

    @abstractmethod
    def get_key_by_hash(self, key_hash: str) -> Optional[ApiKeyMetadata]:
        """Retrieve an API key metadata record by its cryptographic key_hash."""
        pass

    @abstractmethod
    def list_keys(self, include_revoked: bool = True) -> List[ApiKeyMetadata]:
        """List stored API key records, optionally filtering out revoked keys."""
        pass

    @abstractmethod
    def update_key(self, key_meta: ApiKeyMetadata) -> None:
        """Update an existing API key metadata record."""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Delete an API key metadata record completely."""
        pass


class InMemoryApiKeyStore(BaseApiKeyStore):
    """Thread-safe in-memory API key store for development, local execution, and testing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._keys: Dict[str, ApiKeyMetadata] = {}
        self._hash_index: Dict[str, str] = {}  # key_hash -> key_id

    def save_key(self, key_meta: ApiKeyMetadata) -> None:
        with self._lock:
            self._keys[key_meta.key_id] = key_meta
            self._hash_index[key_meta.key_hash] = key_meta.key_id

    def get_key(self, key_id: str) -> Optional[ApiKeyMetadata]:
        with self._lock:
            return self._keys.get(key_id)

    def get_key_by_hash(self, key_hash: str) -> Optional[ApiKeyMetadata]:
        with self._lock:
            key_id = self._hash_index.get(key_hash)
            if key_id:
                return self._keys.get(key_id)
            return None

    def list_keys(self, include_revoked: bool = True) -> List[ApiKeyMetadata]:
        with self._lock:
            keys = list(self._keys.values())
            if include_revoked:
                return keys
            return [k for k in keys if k.revoked_at is None]

    def update_key(self, key_meta: ApiKeyMetadata) -> None:
        with self._lock:
            self._keys[key_meta.key_id] = key_meta
            self._hash_index[key_meta.key_hash] = key_meta.key_id

    def delete_key(self, key_id: str) -> bool:
        with self._lock:
            key_meta = self._keys.pop(key_id, None)
            if key_meta:
                self._hash_index.pop(key_meta.key_hash, None)
                return True
            return False


class MongoApiKeyStore(BaseApiKeyStore):
    """MongoDB storage adapter for API key metadata.
    
    Adheres strictly to the BaseApiKeyStore interface while isolating database dependencies.
    """

    def __init__(
        self,
        collection: Optional[Any] = None,
        uri: Optional[str] = None,
        db_name: str = "xeren",
        collection_name: str = "api_keys",
    ) -> None:
        self._collection = collection
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self._client: Optional[Any] = None

        if self._collection is None and uri:
            self._init_client()

    def _init_client(self) -> None:
        try:
            import pymongo  # type: ignore
            client: Any = pymongo.MongoClient(self.uri)
            self._client = client
            db: Any = client[self.db_name]
            col: Any = db[self.collection_name]
            col.create_index("key_id", unique=True)
            col.create_index("key_hash", unique=True)
            self._collection = col
        except ImportError:
            logger.warning(
                "pymongo is not installed. MongoApiKeyStore requires 'pymongo' to connect to MongoDB."
            )
        except Exception as exc:
            logger.error("Failed to initialize MongoDB client: %s", exc)

    @property
    def collection(self) -> Any:
        """Return the active MongoDB collection or raise RuntimeError if not ready."""
        if self._collection is None:
            raise RuntimeError(
                "MongoApiKeyStore is not connected. Provide an active collection or install pymongo with valid URI."
            )
        return self._collection

    def save_key(self, key_meta: ApiKeyMetadata) -> None:
        doc = key_meta.model_dump(mode="python")
        self.collection.replace_one({"key_id": key_meta.key_id}, doc, upsert=True)

    def get_key(self, key_id: str) -> Optional[ApiKeyMetadata]:
        doc = self.collection.find_one({"key_id": key_id}, {"_id": 0})
        if doc:
            return ApiKeyMetadata.model_validate(doc)
        return None

    def get_key_by_hash(self, key_hash: str) -> Optional[ApiKeyMetadata]:
        doc = self.collection.find_one({"key_hash": key_hash}, {"_id": 0})
        if doc:
            return ApiKeyMetadata.model_validate(doc)
        return None

    def list_keys(self, include_revoked: bool = True) -> List[ApiKeyMetadata]:
        query: Dict[str, Any] = {}
        if not include_revoked:
            query["revoked_at"] = None
        docs = list(self.collection.find(query, {"_id": 0}))
        return [ApiKeyMetadata.model_validate(d) for d in docs]

    def update_key(self, key_meta: ApiKeyMetadata) -> None:
        self.save_key(key_meta)

    def delete_key(self, key_id: str) -> bool:
        res = self.collection.delete_one({"key_id": key_id})
        return bool(getattr(res, "deleted_count", 0) > 0)


__all__ = [
    "BaseApiKeyStore",
    "InMemoryApiKeyStore",
    "MongoApiKeyStore",
]
