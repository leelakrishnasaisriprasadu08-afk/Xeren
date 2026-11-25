"""BasePlatformAdapter — Abstract interface for freelance platforms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from xeren.automation.schemas import PlatformType, WorkOrder, DeliverablePackage


class BasePlatformAdapter(ABC):
    """Unified interface for Fiverr, Upwork, Freelancer, LinkedIn."""

    def __init__(self, platform: PlatformType, credentials: Optional[Dict[str, Any]] = None) -> None:
        self.platform = platform
        self.credentials = credentials or {}

    @abstractmethod
    def fetch_pending_orders(self) -> List[WorkOrder]:
        """Fetch incoming buyer requests or active client orders."""
        pass

    @abstractmethod
    def send_quick_acknowledgment(self, order: WorkOrder) -> str:
        """
        Send an immediate automated acknowledgment to client within minutes
        to maintain high response rate and initiate the engagement.
        """
        pass

    @abstractmethod
    def deliver_work(self, order: WorkOrder, package: DeliverablePackage) -> bool:
        """Submit completed work files and delivery message to platform."""
        pass

    @abstractmethod
    def send_message(self, client_name: str, message: str) -> bool:
        """Send message or progress update to client."""
        pass


__all__ = ["BasePlatformAdapter"]
