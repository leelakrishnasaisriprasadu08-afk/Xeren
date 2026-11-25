"""Freelancer and LinkedIn Platform Adapters."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from xeren.automation.platforms.base import BasePlatformAdapter
from xeren.automation.schemas import PlatformType, WorkOrder, WorkOrderStatus, DeliverablePackage

logger = logging.getLogger("xeren.automation.freelancer_linkedin")


class FreelancerAdapter(BasePlatformAdapter):
    """Freelancer.com platform adapter."""

    def __init__(self, credentials: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(PlatformType.FREELANCER, credentials)
        self._mock_orders: List[WorkOrder] = []

    def fetch_pending_orders(self) -> List[WorkOrder]:
        return [o for o in self._mock_orders if o.status in (WorkOrderStatus.NEW, WorkOrderStatus.ACKNOWLEDGED)]

    def add_simulated_order(self, order: WorkOrder) -> None:
        self._mock_orders.append(order)

    def send_quick_acknowledgment(self, order: WorkOrder) -> str:
        msg = f"Hi {order.client_name}, I have received your project award #{order.order_id}. Commencing execution immediately!"
        order.acknowledgment_sent = True
        order.status = WorkOrderStatus.ACKNOWLEDGED
        return msg

    def deliver_work(self, order: WorkOrder, package: DeliverablePackage) -> bool:
        order.deliverable = package
        order.status = WorkOrderStatus.DELIVERED
        return True

    def send_message(self, client_name: str, message: str) -> bool:
        logger.info("Freelancer message sent to %s: %s", client_name, message)
        return True


class LinkedInAdapter(BasePlatformAdapter):
    """LinkedIn services inquiry & client messaging adapter."""

    def __init__(self, credentials: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(PlatformType.LINKEDIN, credentials)
        self._mock_orders: List[WorkOrder] = []

    def fetch_pending_orders(self) -> List[WorkOrder]:
        return [o for o in self._mock_orders if o.status in (WorkOrderStatus.NEW, WorkOrderStatus.ACKNOWLEDGED)]

    def add_simulated_order(self, order: WorkOrder) -> None:
        self._mock_orders.append(order)

    def send_quick_acknowledgment(self, order: WorkOrder) -> str:
        msg = f"Hello {order.client_name}, thank you for reaching out on LinkedIn regarding this engagement. I have structured the requirements and am preparing the deliverable."
        order.acknowledgment_sent = True
        order.status = WorkOrderStatus.ACKNOWLEDGED
        return msg

    def deliver_work(self, order: WorkOrder, package: DeliverablePackage) -> bool:
        order.deliverable = package
        order.status = WorkOrderStatus.DELIVERED
        return True

    def send_message(self, client_name: str, message: str) -> bool:
        logger.info("LinkedIn message sent to %s: %s", client_name, message)
        return True


__all__ = ["FreelancerAdapter", "LinkedInAdapter"]
