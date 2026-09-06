"""MongoDB adapter for persistent experience storage."""

import logging
from typing import Any, Dict, List, Optional

from xeren.plugins.experience.schemas import ExperienceItem
from xeren.plugins.experience.stores.base import BaseExperienceStore

logger = logging.getLogger("xeren.plugins.experience.stores.mongo")


class MongoExperienceStore(BaseExperienceStore):
    """Production MongoDB adapter for Xeren experience and feedback persistence."""

    def __init__(
        self,
        connection_uri: str = "mongodb://localhost:27017",
        database_name: str = "xeren",
        collection_name: str = "experiences",
        auto_connect: bool = False,
    ) -> None:
        self.connection_uri = connection_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None
        self._connected: bool = False

        if auto_connect:
            self.connect()

    @property
    def is_available(self) -> bool:
        """Check if pymongo is installed in the current environment."""
        try:
            import pymongo  # pyright: ignore[reportMissingImports]
            return True
        except ImportError:
            return False

    @property
    def is_connected(self) -> bool:
        """Check if active MongoDB connection is established."""
        return self._connected and self._collection is not None

    def connect(self) -> bool:
        """Establish connection to MongoDB and ensure indexes."""
        if not self.is_available:
            logger.warning("pymongo is not installed; MongoExperienceStore cannot connect.")
            return False

        try:
            import pymongo  # pyright: ignore[reportMissingImports]
            self._client = pymongo.MongoClient(self.connection_uri, serverSelectionTimeoutMS=2000)
            # Verify connectivity
            self._client.admin.command("ping")
            db = self._client[self.database_name]
            self._collection = db[self.collection_name]

            # Ensure indexes
            self._collection.create_index("id", unique=True)
            self._collection.create_index("content_fingerprint")
            self._collection.create_index("selected_plugin")
            self._collection.create_index("success")
            self._collection.create_index("is_reusable")
            self._collection.create_index([("timestamp", -1)])

            self._connected = True
            logger.info("MongoExperienceStore connected successfully to %s", self.database_name)
            return True
        except Exception as exc:
            logger.warning("Failed to connect MongoExperienceStore to %s: %s", self.connection_uri, exc)
            self._connected = False
            return False

    def _ensure_collection(self) -> Any:
        if not self._connected or self._collection is None:
            success = self.connect()
            if not success or self._collection is None:
                raise RuntimeError(
                    "MongoExperienceStore is not connected to a live MongoDB instance. "
                    "Ensure MongoDB is running and pymongo is installed, or use InMemoryExperienceStore."
                )
        return self._collection

    def add(self, item: ExperienceItem) -> str:
        coll = self._ensure_collection()
        fp = item.content_fingerprint or item.generate_fingerprint()
        item = item.model_copy(update={"content_fingerprint": fp})
        doc = item.model_dump(mode="json")
        coll.replace_one({"id": item.id}, doc, upsert=True)
        return item.id

    def get(self, item_id: str) -> Optional[ExperienceItem]:
        coll = self._ensure_collection()
        doc = coll.find_one({"id": item_id}, {"_id": 0})
        if doc:
            return ExperienceItem.model_validate(doc)
        return None

    def get_by_fingerprint(self, fingerprint: str) -> Optional[ExperienceItem]:
        coll = self._ensure_collection()
        doc = coll.find_one({"content_fingerprint": fingerprint}, {"_id": 0})
        if doc:
            return ExperienceItem.model_validate(doc)
        return None

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[ExperienceItem]:
        coll = self._ensure_collection()
        mongo_filter: Dict[str, Any] = {}

        if filters:
            if "success" in filters:
                mongo_filter["success"] = filters["success"]
            if "selected_plugin" in filters:
                mongo_filter["selected_plugin"] = filters["selected_plugin"]
            if "is_reusable" in filters:
                mongo_filter["is_reusable"] = filters["is_reusable"]
            if "verification_status" in filters:
                mongo_filter["verification_status"] = filters["verification_status"]
            if "tag" in filters:
                mongo_filter["tags"] = filters["tag"]

        if query:
            mongo_filter["$or"] = [
                {"task": {"$regex": query, "$options": "i"}},
                {"context": {"$regex": query, "$options": "i"}},
                {"action": {"$regex": query, "$options": "i"}},
                {"lesson": {"$regex": query, "$options": "i"}},
                {"failure_reason": {"$regex": query, "$options": "i"}},
            ]

        cursor = coll.find(mongo_filter, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return [ExperienceItem.model_validate(doc) for doc in cursor]

    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
        coll = self._ensure_collection()
        res = coll.update_one({"id": item_id}, {"$set": updates})
        return bool(res.matched_count > 0)

    def delete(self, item_id: str) -> bool:
        coll = self._ensure_collection()
        res = coll.delete_one({"id": item_id})
        return bool(res.deleted_count > 0)

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        coll = self._ensure_collection()
        mongo_filter: Dict[str, Any] = {}
        if filters:
            for k, v in filters.items():
                mongo_filter[k] = v
        return int(coll.count_documents(mongo_filter))

    def clear(self) -> None:
        coll = self._ensure_collection()
        coll.delete_many({})
