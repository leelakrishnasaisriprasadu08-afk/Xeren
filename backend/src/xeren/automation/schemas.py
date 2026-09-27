"""Schemas for Multi-Platform Freelance Automation & Workspaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class PlatformType(str, Enum):
    FIVERR = "fiverr"
    UPWORK = "upwork"
    FREELANCER = "freelancer"
    LINKEDIN = "linkedin"


class WorkOrderStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    REVIEW_READY = "review_ready"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ClientBrief:
    """Structured requirements extracted from client order."""
    project_type: str  # e.g., "website", "python_script", "data_cleaning", "research_report"
    raw_prompt: str
    target_deliverables: List[str] = field(default_factory=list)
    client_tone: str = "professional"
    constraints: List[str] = field(default_factory=list)


@dataclass
class DeliverablePackage:
    """Packaged deliverable ready for platform submission."""
    order_id: str
    files: List[str]
    delivery_note: str
    zip_archive_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WorkOrder:
    """An autonomous freelance order or client contract."""
    order_id: str
    platform: PlatformType
    client_name: str
    amount_usd: float
    deadline_iso: str
    status: WorkOrderStatus = WorkOrderStatus.NEW
    brief: Optional[ClientBrief] = None
    workspace_directory: str = ""
    deliverable: Optional[DeliverablePackage] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledgment_sent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "PlatformType",
    "WorkOrderStatus",
    "ClientBrief",
    "DeliverablePackage",
    "WorkOrder",
]
