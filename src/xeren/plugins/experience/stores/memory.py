"""In-memory implementation of BaseExperienceStore for fast local testing and zero-dependency execution."""

import re
import threading
from typing import Any, Dict, List, Optional

from xeren.plugins.experience.schemas import ExperienceItem
from xeren.plugins.experience.stores.base import BaseExperienceStore


class InMemoryExperienceStore(BaseExperienceStore):
    """Thread-safe, zero-dependency in-memory experience store."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: Dict[str, ExperienceItem] = {}
        self._fingerprint_index: Dict[str, str] = {}  # fingerprint -> item_id

    def add(self, item: ExperienceItem) -> str:
        with self._lock:
            fp = item.content_fingerprint or item.generate_fingerprint()
            item = item.model_copy(update={"content_fingerprint": fp})
            self._items[item.id] = item
            if fp:
                self._fingerprint_index[fp] = item.id
            return item.id

    def get(self, item_id: str) -> Optional[ExperienceItem]:
        with self._lock:
            return self._items.get(item_id)

    def get_by_fingerprint(self, fingerprint: str) -> Optional[ExperienceItem]:
        with self._lock:
            item_id = self._fingerprint_index.get(fingerprint)
            if item_id:
                return self._items.get(item_id)
            return None

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[ExperienceItem]:
        with self._lock:
            results: List[ExperienceItem] = []
            query_tokens = (
                [t.lower() for t in re.findall(r"\w+", query)] if query else []
            )

            for item in self._items.values():
                # Apply filters
                if filters:
                    if "success" in filters and item.success != filters["success"]:
                        continue
                    if (
                        "selected_plugin" in filters
                        and item.selected_plugin != filters["selected_plugin"]
                    ):
                        continue
                    if (
                        "is_reusable" in filters
                        and item.is_reusable != filters["is_reusable"]
                    ):
                        continue
                    if (
                        "verification_status" in filters
                        and item.verification_status != filters["verification_status"]
                    ):
                        continue
                    if "tag" in filters and filters["tag"] not in item.tags:
                        continue

                # Apply text query match if query provided
                if query_tokens:
                    searchable_text = " ".join(
                        filter(
                            None,
                            [
                                item.task,
                                item.selected_plugin or "",
                                item.context or "",
                                item.action or "",
                                item.lesson or "",
                                item.failure_reason or "",
                                item.failure_avoidance_advice or "",
                                item.error or "",
                                " ".join(item.tags),
                            ],
                        )
                    ).lower()
                    # Check overlap
                    matched = sum(1 for t in query_tokens if t in searchable_text)
                    if matched == 0:
                        continue

                results.append(item)

            # Sort descending by timestamp
            results.sort(key=lambda x: x.timestamp, reverse=True)
            return results[:limit]

    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
        with self._lock:
            existing = self._items.get(item_id)
            if not existing:
                return False
            updated = existing.model_copy(update=updates)
            self._items[item_id] = updated
            # Update fingerprint if modified
            if updated.content_fingerprint:
                self._fingerprint_index[updated.content_fingerprint] = item_id
            return True

    def delete(self, item_id: str) -> bool:
        with self._lock:
            existing = self._items.pop(item_id, None)
            if existing:
                if existing.content_fingerprint in self._fingerprint_index:
                    del self._fingerprint_index[existing.content_fingerprint]
                return True
            return False

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        with self._lock:
            if not filters:
                return len(self._items)
            return len(self.search(filters=filters, limit=len(self._items) + 1))

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._fingerprint_index.clear()
