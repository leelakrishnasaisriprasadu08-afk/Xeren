"""Abstract base interface for experience storage backends."""

from abc import ABC, abstractmethod
import asyncio
from typing import Any, Dict, List, Optional

from xeren.plugins.experience.schemas import ExperienceItem


class BaseExperienceStore(ABC):
    """Abstract interface defining required storage operations for experience records."""

    @abstractmethod
    def add(self, item: ExperienceItem) -> str:
        """Store an experience item and return its identifier."""
        pass

    async def aadd(self, item: ExperienceItem) -> str:
        """Asynchronously store an experience item."""
        return await asyncio.to_thread(self.add, item)

    @abstractmethod
    def get(self, item_id: str) -> Optional[ExperienceItem]:
        """Retrieve an experience item by its unique ID."""
        pass

    async def aget(self, item_id: str) -> Optional[ExperienceItem]:
        """Asynchronously retrieve an experience item by ID."""
        return await asyncio.to_thread(self.get, item_id)

    @abstractmethod
    def get_by_fingerprint(self, fingerprint: str) -> Optional[ExperienceItem]:
        """Retrieve an experience item by its content SHA-256 fingerprint for deduplication."""
        pass

    async def aget_by_fingerprint(self, fingerprint: str) -> Optional[ExperienceItem]:
        """Asynchronously retrieve an experience item by fingerprint."""
        return await asyncio.to_thread(self.get_by_fingerprint, fingerprint)

    @abstractmethod
    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[ExperienceItem]:
        """Search and filter experience records."""
        pass

    async def asearch(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[ExperienceItem]:
        """Asynchronously search and filter experience records."""
        return await asyncio.to_thread(self.search, query, filters, limit)

    @abstractmethod
    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update fields of an existing experience record."""
        pass

    async def aupdate(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Asynchronously update an existing experience record."""
        return await asyncio.to_thread(self.update, item_id, updates)

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """Delete an experience record by ID."""
        pass

    async def adelete(self, item_id: str) -> bool:
        """Asynchronously delete an experience record."""
        return await asyncio.to_thread(self.delete, item_id)

    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total matching stored experiences."""
        pass

    async def acount(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Asynchronously count matching stored experiences."""
        return await asyncio.to_thread(self.count, filters)

    @abstractmethod
    def clear(self) -> None:
        """Wipe all experience records from store."""
        pass

    async def aclear(self) -> None:
        """Asynchronously wipe all experience records."""
        await asyncio.to_thread(self.clear)
