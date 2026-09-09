"""Unit tests for Multi-Platform Freelance Automation (Fiverr, Upwork, Freelancer, LinkedIn)."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from xeren.automation.schemas import PlatformType, WorkOrderStatus
from xeren.automation.manager import MultiWorkspaceManager
from xeren.automation.platforms.fiverr import FiverrAdapter
from xeren.automation.platforms.upwork import UpworkAdapter


class TestMultiPlatformWorkspaces:
    def test_fiverr_order_intake_and_rapid_response(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "workspaces"
            mgr = MultiWorkspaceManager(base_workspaces_dir=base_dir)

            order = mgr.register_incoming_order(
                order_id="FIVERR-9821",
                platform=PlatformType.FIVERR,
                client_name="Sarah Miller",
                amount_usd=250.0,
                brief_prompt="Build a clean landing page for an organic tea brand",
                project_type="website",
            )

            assert order.status == WorkOrderStatus.ACKNOWLEDGED
            assert order.acknowledgment_sent is True
            assert Path(order.workspace_directory).exists()

    def test_fiverr_order_pipeline_execution_and_delivery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "workspaces"
            mgr = MultiWorkspaceManager(base_workspaces_dir=base_dir)

            order = mgr.register_incoming_order(
                order_id="FIVERR-9821",
                platform=PlatformType.FIVERR,
                client_name="Sarah Miller",
                amount_usd=250.0,
                brief_prompt="Build an organic tea website",
                project_type="website",
            )

            package = mgr.execute_order_pipeline(order.order_id)
            assert package.order_id == "FIVERR-9821"
            assert len(package.files) >= 2
            assert all(Path(f).exists() for f in package.files)

            updated_order = mgr.get_order("FIVERR-9821")
            assert updated_order.status == WorkOrderStatus.DELIVERED
            assert updated_order.deliverable is not None

    def test_upwork_contract_workspace_isolation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "workspaces"
            mgr = MultiWorkspaceManager(base_workspaces_dir=base_dir)

            order_upwork = mgr.register_incoming_order(
                order_id="UPWORK-402",
                platform=PlatformType.UPWORK,
                client_name="Apex Corp",
                amount_usd=1200.0,
                brief_prompt="Python script for market log extraction",
                project_type="coding",
            )

            order_fiverr = mgr.register_incoming_order(
                order_id="FIVERR-101",
                platform=PlatformType.FIVERR,
                client_name="Bob",
                amount_usd=50.0,
                brief_prompt="Simple logo site",
                project_type="website",
            )

            # Assert strict filesystem isolation
            assert order_upwork.workspace_directory != order_fiverr.workspace_directory
            assert "upwork" in order_upwork.workspace_directory
            assert "fiverr" in order_fiverr.workspace_directory
