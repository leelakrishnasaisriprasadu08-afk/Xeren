"""Base interface for internal research tools."""

from abc import ABC, abstractmethod
import asyncio
from typing import Any


class BaseResearchTool(ABC):
    """Abstract base class for internal tools used by the Research Workflow."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool accomplishes."""
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronously execute tool logic."""
        pass

    async def aexecute(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously execute tool logic."""
        return await asyncio.to_thread(self.execute, *args, **kwargs)


__all__ = ["BaseResearchTool"]
