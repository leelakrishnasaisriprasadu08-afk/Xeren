"""Upwork Platform Adapter — Job proposals, contract milestones, client messaging."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from xeren.automation.platforms.base import BasePlatformAdapter
from xeren.automation.schemas import PlatformType, WorkOrder, WorkOrderStatus, DeliverablePackage

logger = logging.getLogger("xeren.automation.upwork")


class UpworkAdapter(BasePlatformAdapter):
    """
    Upwork automation adapter:
    - Analyzes contract milestones
    - Rapid response to client inquiries
    - Milestone deliverable submissions
    """

    def __init__(self, credentials: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(PlatformType.UPWORK, credentials)
        self._mock_orders: List[WorkOrder] = []

    def fetch_pending_orders(self) -> List[WorkOrder]:
        return [o for o in self._mock_orders if o.status in (WorkOrderStatus.NEW, WorkOrderStatus.ACKNOWLEDGED)]

    def add_simulated_order(self, order: WorkOrder) -> None:
        self._mock_orders.append(order)

    def send_quick_acknowledgment(self, order: WorkOrder) -> str:
        msg = (
            f"Hello {order.client_name}, confirming receipt of milestone #{order.order_id}. "
            f"I have initialized the project workspace and am executing the technical specifications as outlined."
        )
        order.acknowledgment_sent = True
        order.status = WorkOrderStatus.ACKNOWLEDGED
        logger.info("Upwork acknowledgment sent for contract %s", order.order_id)
        return msg

    def deliver_work(self, order: WorkOrder, package: DeliverablePackage) -> bool:
        order.deliverable = package
        order.status = WorkOrderStatus.DELIVERED
        logger.info("Upwork milestone submitted for order %s", order.order_id)
        return True

    def send_message(self, client_name: str, message: str) -> bool:
        logger.info("Upwork message sent to %s: %s", client_name, message)
        return True


__all__ = ["UpworkAdapter"]
