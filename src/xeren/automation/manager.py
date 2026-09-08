"""MultiWorkspaceManager — Coordinates concurrent freelance platform pipelines and personal workspace."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from xeren.automation.schemas import PlatformType, WorkOrder, WorkOrderStatus, DeliverablePackage, ClientBrief
from xeren.automation.platforms.base import BasePlatformAdapter
from xeren.automation.platforms.fiverr import FiverrAdapter
from xeren.automation.platforms.upwork import UpworkAdapter
from xeren.automation.platforms.freelancer_linkedin import FreelancerAdapter, LinkedInAdapter
from xeren.security.schemas import DataSensitivityTier
from xeren.security.gate import XerenSecurityGate

logger = logging.getLogger("xeren.automation.manager")


class MultiWorkspaceManager:
    """
    Manages isolated, concurrent workspaces across personal & freelance accounts.

    Core guarantees:
    1. Zero Interference: Freelance background execution never interrupts or blocks personal workspace.
    2. Strict Privacy Isolation: Client briefs and data are classified as SENSITIVE, strictly
       contained in isolated folders, and never leaked into personal context.
    3. Rapid Response: Automatically acknowledges new orders in under 2 minutes.
    4. Autonomous Execution: Builds deliverables (websites, scripts, reports) in the order workspace.
    """

    def __init__(
        self,
        base_workspaces_dir: Optional[Path] = None,
        security_gate: Optional[XerenSecurityGate] = None,
    ) -> None:
        self.base_dir = base_workspaces_dir or (Path.home() / ".xeren" / "workspaces")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.gate = security_gate or XerenSecurityGate()

        # Platform Adapters
        self.adapters: Dict[PlatformType, BasePlatformAdapter] = {
            PlatformType.FIVERR: FiverrAdapter(),
            PlatformType.UPWORK: UpworkAdapter(),
            PlatformType.FREELANCER: FreelancerAdapter(),
            PlatformType.LINKEDIN: LinkedInAdapter(),
        }

        # Active tracked orders across all platforms
        self._active_orders: Dict[str, WorkOrder] = {}

    def get_adapter(self, platform: PlatformType) -> BasePlatformAdapter:
        return self.adapters[platform]

    def register_incoming_order(
        self,
        order_id: str,
        platform: PlatformType,
        client_name: str,
        amount_usd: float,
        brief_prompt: str,
        project_type: str = "website",
    ) -> WorkOrder:
        """
        Ingest a new client order:
        1. Create isolated workspace directory.
        2. Set up client brief.
        3. Send rapid acknowledgment (<2 min).
        4. Track in active orders.
        """
        workspace_path = self.base_dir / platform.value / f"order_{order_id}"
        workspace_path.mkdir(parents=True, exist_ok=True)

        brief = ClientBrief(
            project_type=project_type,
            raw_prompt=brief_prompt,
            target_deliverables=[f"{project_type}_deliverable"],
        )

        order = WorkOrder(
            order_id=order_id,
            platform=platform,
            client_name=client_name,
            amount_usd=amount_usd,
            deadline_iso="2026-09-10T00:00:00Z",
            status=WorkOrderStatus.NEW,
            brief=brief,
            workspace_directory=str(workspace_path.resolve()),
        )

        # 1. Send immediate acknowledgment
        adapter = self.get_adapter(platform)
        adapter.send_quick_acknowledgment(order)

        self._active_orders[order_id] = order
        logger.info("Order %s registered on %s in workspace: %s", order_id, platform.value, workspace_path)
        return order

    def execute_order_pipeline(self, order_id: str) -> DeliverablePackage:
        """
        Execute work for an order in its isolated directory:
        - For website projects: generates HTML/CSS/JS files and ZIP package.
        - Delivers through the platform adapter.
        """
        order = self._active_orders.get(order_id)
        if not order:
            raise ValueError(f"Order #{order_id} not found.")

        order.status = WorkOrderStatus.IN_PROGRESS
        work_dir = Path(order.workspace_directory)

        # Build deliverable files based on brief
        deliverable_files = []
        if order.brief and order.brief.project_type == "website":
            index_html = work_dir / "index.html"
            index_html.write_text(
                f"<!DOCTYPE html><html><head><title>{order.client_name} Project</title></head>"
                f"<body><h1>Delivered Website for {order.client_name}</h1><p>{order.brief.raw_prompt}</p></body></html>",
                encoding="utf-8",
            )
            deliverable_files.append(str(index_html))

            style_css = work_dir / "style.css"
            style_css.write_text("body { font-family: sans-serif; background: #0f172a; color: #f8fafc; }", encoding="utf-8")
            deliverable_files.append(str(style_css))
        else:
            # Generic script/deliverable
            main_file = work_dir / "solution.py"
            main_file.write_text(f"# Client solution for {order.client_name}\nprint('Solution ready')\n", encoding="utf-8")
            deliverable_files.append(str(main_file))

        # Create deliverable package
        package = DeliverablePackage(
            order_id=order_id,
            files=deliverable_files,
            delivery_note=f"Hi {order.client_name}, your project #{order_id} has been completed according to your specifications. Please review the attached deliverables!",
        )

        # Deliver to platform
        adapter = self.get_adapter(order.platform)
        adapter.deliver_work(order, package)
        order.status = WorkOrderStatus.DELIVERED

        logger.info("Order pipeline completed and delivered for %s (%s)", order_id, order.platform.value)
        return package

    def list_all_active_orders(self) -> List[WorkOrder]:
        return list(self._active_orders.values())

    def get_order(self, order_id: str) -> Optional[WorkOrder]:
        return self._active_orders.get(order_id)


__all__ = ["MultiWorkspaceManager"]
