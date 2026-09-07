"""MongoDB Connection Manager & Hybrid Persistence Layer for Xeren.

Supports MongoDB Atlas (Free M0 / Dedicated) and local MongoDB instances,
providing live connection verification (ping latency, cluster info, collection stats)
with an offline hybrid fallback to maintain 100% workstation uptime.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("xeren.db.mongo")

try:
    import pymongo
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


class MongoConnectionManager:
    """Manages MongoDB Atlas and local connections with telemetry and fallback."""

    def __init__(
        self,
        default_uri: Optional[str] = None,
        db_name: str = "xeren_workspace",
    ) -> None:
        self.uri = default_uri or os.getenv("MONGODB_URI", "")
        self.db_name = db_name
        self._sync_client: Optional[Any] = None
        self._connected = False
        self._last_ping_ms: Optional[float] = None
        self._last_checked_at: Optional[str] = None
        self._server_version: Optional[str] = None
        self._cluster_mode: str = "offline_fallback"
        self._collections: List[str] = []
        self._fallback_store: Dict[str, Dict[str, Dict[str, Any]]] = {
            "users": {},
            "projects": {},
            "invites": {},
            "activity_logs": {},
        }

        # Attempt initial verification if URI is configured
        if self.uri and PYMONGO_AVAILABLE:
            self.verify_connection(self.uri, self.db_name, timeout_ms=2000)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def verify_connection(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
        timeout_ms: int = 3500,
    ) -> Dict[str, Any]:
        """Test and verify MongoDB connectivity, measuring roundtrip ping latency."""
        target_uri = uri or self.uri
        target_db = db_name or self.db_name

        if not target_uri:
            self._connected = False
            self._cluster_mode = "offline_fallback"
            return {
                "connected": False,
                "mode": "offline_fallback",
                "message": "No MongoDB connection string configured. Running in high-performance local fallback mode.",
                "database": target_db,
                "latency_ms": None,
                "server_version": "Local Virtual Store",
                "collections": list(self._fallback_store.keys()),
            }

        if not PYMONGO_AVAILABLE:
            return {
                "connected": False,
                "mode": "offline_fallback",
                "message": "pymongo package not available. Running in local fallback mode.",
                "database": target_db,
                "latency_ms": None,
                "server_version": "Local Virtual Store",
                "collections": list(self._fallback_store.keys()),
            }

        try:
            start_time = time.perf_counter()
            client = pymongo.MongoClient(
                target_uri,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
            )
            # Run admin command ping
            client.admin.command("ping")
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Retrieve server info and collections
            server_info = client.server_info()
            version = server_info.get("version", "Unknown")
            db = client[target_db]
            collections = db.list_collection_names()

            # Identify cluster mode (Atlas cloud vs local)
            is_atlas = "mongodb+srv" in target_uri or "mongodb.net" in target_uri
            cluster_mode = "atlas_cloud" if is_atlas else "local_mongodb"

            # Cache successful client
            self.uri = target_uri
            self.db_name = target_db
            self._sync_client = client
            self._connected = True
            self._last_ping_ms = elapsed_ms
            self._last_checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._server_version = version
            self._cluster_mode = cluster_mode
            self._collections = collections

            logger.info("MongoDB successfully verified: mode=%s, latency=%.2fms", cluster_mode, elapsed_ms)
            return {
                "connected": True,
                "mode": cluster_mode,
                "message": f"Connected to MongoDB ({cluster_mode}) successfully.",
                "database": target_db,
                "latency_ms": elapsed_ms,
                "server_version": version,
                "collections": collections,
                "checked_at": self._last_checked_at,
            }
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as exc:
            self._connected = False
            self._cluster_mode = "offline_fallback"
            logger.warning("MongoDB connection verification failed: %s. Using fallback store.", exc)
            return {
                "connected": False,
                "mode": "offline_fallback",
                "message": f"Connection check failed ({type(exc).__name__}): {exc}",
                "database": target_db,
                "latency_ms": None,
                "server_version": "Local Virtual Store",
                "collections": list(self._fallback_store.keys()),
                "error": str(exc),
            }

    def get_status(self) -> Dict[str, Any]:
        """Return cached status of database connectivity."""
        return {
            "connected": self._connected,
            "mode": self._cluster_mode,
            "database": self.db_name,
            "latency_ms": self._last_ping_ms,
            "server_version": self._server_version or "Local Virtual Store",
            "collections": self._collections if self._connected else list(self._fallback_store.keys()),
            "last_checked_at": self._last_checked_at,
            "uri_configured": bool(self.uri),
            "masked_uri": self._mask_uri(self.uri) if self.uri else None,
        }

    def _mask_uri(self, uri: str) -> str:
        """Mask credentials in MongoDB connection string for safe UI presentation."""
        try:
            if "@" in uri:
                prefix = uri.split("@")[0]
                suffix = uri.split("@")[1]
                scheme = prefix.split("://")[0]
                return f"{scheme}://••••:••••@{suffix}"
            return uri
        except Exception:
            return "mongodb://••••••••"

    # --- Resilient Collection Interface (MongoDB with seamless fallback) ---

    def insert_document(self, collection_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or replace a document in the target collection."""
        if self._connected and self._sync_client:
            try:
                db = self._sync_client[self.db_name]
                db[collection_name].replace_one({"_id": doc_id}, {**doc, "_id": doc_id}, upsert=True)
            except Exception as e:
                logger.warning("MongoDB write failed, updating local fallback: %s", e)

        # Always update local fallback for offline instant read
        if collection_name not in self._fallback_store:
            self._fallback_store[collection_name] = {}
        self._fallback_store[collection_name][doc_id] = dict(doc)
        return doc

    def find_document(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Find a single document by ID."""
        if self._connected and self._sync_client:
            try:
                db = self._sync_client[self.db_name]
                res = db[collection_name].find_one({"_id": doc_id})
                if res:
                    res.pop("_id", None)
                    return res
            except Exception as e:
                logger.warning("MongoDB read failed, falling back: %s", e)

        col = self._fallback_store.get(collection_name, {})
        return col.get(doc_id)

    def list_documents(self, collection_name: str) -> List[Dict[str, Any]]:
        """List all documents in a collection."""
        if self._connected and self._sync_client:
            try:
                db = self._sync_client[self.db_name]
                docs = list(db[collection_name].find())
                for d in docs:
                    d.pop("_id", None)
                return docs
            except Exception as e:
                logger.warning("MongoDB list failed, falling back: %s", e)

        col = self._fallback_store.get(collection_name, {})
        return list(col.values())

    def delete_document(self, collection_name: str, doc_id: str) -> bool:
        """Delete a document by ID."""
        if self._connected and self._sync_client:
            try:
                db = self._sync_client[self.db_name]
                db[collection_name].delete_one({"_id": doc_id})
            except Exception as e:
                logger.warning("MongoDB delete failed: %s", e)

        if collection_name in self._fallback_store and doc_id in self._fallback_store[collection_name]:
            del self._fallback_store[collection_name][doc_id]
            return True
        return False


# Global singleton instance
mongo_manager = MongoConnectionManager()
