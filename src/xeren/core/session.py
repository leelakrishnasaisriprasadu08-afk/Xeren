"""XerenSession — Active session management with security context and workspace scopes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from xeren.security.schemas import DataSensitivityTier
from xeren.security.session_lock import SessionLockManager
from xeren.security.pin_store import PinStore
from xeren.security.gate import XerenSecurityGate
from xeren.security.memory_fence import SecureMemoryFence
from xeren.core.vault import UserVault

logger = logging.getLogger("xeren.core.session")


class XerenSession:
    """
    Encapsulates the current interactive user session.

    Coordinates:
    - User authentication and PIN verification
    - Session-scoped 3-tier unlocking (silent 30m/10m activity windows)
    - Active workspace pointer (Personal vs. Freelance Account)
    - Automatic memory zeroing on close
    """

    def __init__(
        self,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        vault: Optional[UserVault] = None,
        pin_store: Optional[PinStore] = None,
    ) -> None:
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now(timezone.utc)
        self.vault = vault or UserVault()
        self.pin_store = pin_store or PinStore()

        # Session lock manager bound to this user & pin store
        self.lock_manager = SessionLockManager(user_id=self.user_id, pin_store=self.pin_store)
        self.fence = SecureMemoryFence()
        self.gate = XerenSecurityGate(session_lock=self.lock_manager)

        # Active workspace context: "personal", "fiverr", "upwork", etc.
        self.active_workspace_type: str = "personal"
        self.active_workspace_id: Optional[str] = None

        # Interactive planning & task gating state
        self.active_plan: Optional[Any] = None
        self.staged_plan_status: str = "idle"  # "idle", "staged", "executing", "completed"
        self.conversation_history: List[Dict[str, Any]] = []

        logger.info("XerenSession initialized: id=%s user=%s", self.session_id, self.user_id)

    # ------------------------------------------------------------------
    # Task Plan Staging & Approval
    # ------------------------------------------------------------------

    def stage_plan(self, plan: Any) -> None:
        """Stage a planned task awaiting user's explicit 'proceed to the plan' approval."""
        self.active_plan = plan
        self.staged_plan_status = "staged"
        logger.info("Plan staged in session %s for goal: %s", self.session_id, getattr(plan, "goal", "custom"))

    def get_staged_plan(self) -> Optional[Any]:
        """Fetch the currently staged plan."""
        return self.active_plan

    def clear_staged_plan(self) -> None:
        """Clear active plan after execution or rejection."""
        self.active_plan = None
        self.staged_plan_status = "idle"

    def record_turn(self, role: str, content: str) -> None:
        """Record a chat turn in session conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 50 turns
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

    # ------------------------------------------------------------------
    # Authentication & Unlocking
    # ------------------------------------------------------------------

    def unlock_tier_with_pin(self, tier: DataSensitivityTier, pin: str) -> bool:
        """Unlock Sensitive or More Sensitive tier for this session."""
        success = self.lock_manager.verify_and_unlock(tier=tier, pin=pin)
        if success:
            logger.info("Session %s unlocked tier %s", self.session_id, tier.value)
        return success

    def is_tier_accessible(self, tier: DataSensitivityTier) -> bool:
        """Check if tier can be accessed without challenge."""
        return self.lock_manager.is_unlocked(tier)

    # ------------------------------------------------------------------
    # Workspace Context
    # ------------------------------------------------------------------

    def set_active_workspace(self, workspace_type: str, workspace_id: Optional[str] = None) -> None:
        """Switch current focal workspace without interrupting background workspaces."""
        self.active_workspace_type = workspace_type
        self.active_workspace_id = workspace_id
        logger.info("Active workspace set to: %s (id=%s)", workspace_type, workspace_id)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Lock all tiers and securely wipe sensitive buffers on session end."""
        self.lock_manager.lock_all()
        logger.info("Session %s closed and locked.", self.session_id)


__all__ = ["XerenSession"]
