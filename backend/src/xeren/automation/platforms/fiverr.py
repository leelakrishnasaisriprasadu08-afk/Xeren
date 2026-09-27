"""Fiverr Platform Adapter — Gigs, buyer orders, rapid response, and deliveries."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from xeren.automation.platforms.base import BasePlatformAdapter
from xeren.automation.schemas import PlatformType, WorkOrder, WorkOrderStatus, DeliverablePackage, ClientBrief

logger = logging.getLogger("xeren.automation.fiverr")


class FiverrAdapter(BasePlatformAdapter):
    """
    Fiverr automation adapter:
    - Automatically acknowledges incoming orders in under 2 minutes
    - Coordinates isolated gig workspaces
    - Formats deliverable notes and package archives
    """

    def __init__(self, credentials: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(PlatformType.FIVERR, credentials)
        self._mock_orders: List[WorkOrder] = []

    def fetch_pending_orders(self) -> List[WorkOrder]:
        """Fetch active Fiverr orders."""
        return [o for o in self._mock_orders if o.status in (WorkOrderStatus.NEW, WorkOrderStatus.ACKNOWLEDGED)]

    def add_simulated_order(self, order: WorkOrder) -> None:
        """Helper to enqueue an incoming order for processing."""
        self._mock_orders.append(order)

    def send_quick_acknowledgment(self, order: WorkOrder) -> str:
        """Rapid professional acknowledgment for Fiverr buyer."""
        msg = (
            f"Hi {order.client_name}! Thank you for placing your order #{order.order_id}. "
            f"I have reviewed your requirements and started working on your project right away. "
            f"I'll update you as soon as the initial milestone is ready!"
        )
        order.acknowledgment_sent = True
        order.status = WorkOrderStatus.ACKNOWLEDGED
        logger.info("Fiverr rapid response sent for order %s to %s", order.order_id, order.client_name)
        return msg

    def deliver_work(self, order: WorkOrder, package: DeliverablePackage) -> bool:
        """Deliver completed order to buyer."""
        order.deliverable = package
        order.status = WorkOrderStatus.DELIVERED
        logger.info("Fiverr order %s successfully marked as DELIVERED.", order.order_id)
        return True

    def send_message(self, client_name: str, message: str) -> bool:
        logger.info("Fiverr message sent to %s: %s", client_name, message)
        return True


__all__ = ["FiverrAdapter"]
