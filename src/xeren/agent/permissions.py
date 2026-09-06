"""Permission Manager enforcing safety boundaries, human-in-the-loop approvals, and risk policies."""

from enum import Enum
import logging
from typing import Dict, Optional, Set, Tuple

from xeren.agent.types import ActionCategory, AgentAction

logger = logging.getLogger("xeren.agent.permissions")


class PermissionMode(str, Enum):
    """Enforcement mode for PermissionManager."""

    STRICT = "strict"  # Requires explicit approval for all consequential/interactive actions
    AUTO_APPROVE = "auto_approve"  # Auto-approves safe and interactive; consequential still checked
    INTERACTIVE = "interactive"  # Standard interactive human-in-the-loop


class PermissionManager:
    """Evaluates agent actions against security risk categories and manages approvals."""

    CONSEQUENTIAL_TYPES: Set[str] = {
        "upload",
        "download",
        "delete",
        "submit",
        "purchase",
        "execute_code",
        "system_command",
        "modify_data",
    }

    def __init__(
        self,
        mode: PermissionMode = PermissionMode.AUTO_APPROVE,
        require_consequential_approval: bool = True,
    ) -> None:
        self.mode = mode
        self.require_consequential_approval = require_consequential_approval
        self._pending_approvals: Dict[str, AgentAction] = {}
        self._decision_history: Dict[str, bool] = {}

    def classify_action(self, action: AgentAction) -> ActionCategory:
        """Categorize action into risk levels."""
        action_name = action.action_type.lower()
        if action.consequential or action_name in self.CONSEQUENTIAL_TYPES:
            return ActionCategory.CONSEQUENTIAL
        if action_name in {"observe", "extract", "inspect", "get", "query"}:
            return ActionCategory.READ_ONLY
        if action_name in {"navigate", "click", "type", "select", "scroll", "wait"}:
            return ActionCategory.INTERACTIVE
        return ActionCategory.INTERACTIVE

    def is_consequential(self, action: AgentAction) -> bool:
        """Check if action is classified as consequential."""
        return self.classify_action(action) == ActionCategory.CONSEQUENTIAL

    def check_permission(self, action: AgentAction) -> Tuple[bool, Optional[str]]:
        """Check whether action is permitted to execute under current policy."""
        category = self.classify_action(action)

        # 1. Consequential actions require explicit approval if configured
        if category == ActionCategory.CONSEQUENTIAL and self.require_consequential_approval:
            if action.action_id in self._decision_history:
                allowed = self._decision_history[action.action_id]
                return (allowed, None if allowed else "Action was explicitly denied by user.")
            # Action has not yet been approved
            self._pending_approvals[action.action_id] = action
            return (False, f"Action '{action.action_type}' is consequential and requires user approval.")

        # 2. Strict mode checks interactive actions as well
        if self.mode == PermissionMode.STRICT and category in {ActionCategory.INTERACTIVE, ActionCategory.CONSEQUENTIAL}:
            if action.action_id in self._decision_history:
                allowed = self._decision_history[action.action_id]
                return (allowed, None if allowed else "Action was explicitly denied in strict mode.")
            self._pending_approvals[action.action_id] = action
            return (False, f"Strict mode requires approval for '{action.action_type}'.")

        # 3. Safe read-only or auto-approved
        return (True, None)

    def grant_approval(self, action_id: str) -> bool:
        """Approve a pending action."""
        if action_id in self._pending_approvals:
            self._pending_approvals.pop(action_id)
        self._decision_history[action_id] = True
        logger.info("Granted permission for action ID: %s", action_id)
        return True

    def deny_approval(self, action_id: str, reason: Optional[str] = None) -> bool:
        """Deny a pending action."""
        if action_id in self._pending_approvals:
            self._pending_approvals.pop(action_id)
        self._decision_history[action_id] = False
        logger.warning("Denied permission for action ID %s. Reason: %s", action_id, reason or "Denied by user policy")
        return False

    def list_pending(self) -> Dict[str, AgentAction]:
        """Return all actions awaiting approval."""
        return dict(self._pending_approvals)


__all__ = ["PermissionMode", "PermissionManager"]
