"""XerenSecurityGate — 8-layer security orchestrator for all data access."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Optional

from xeren.security.audit import SecurityAuditLogger
from xeren.security.classification import DataClassifier
from xeren.security.memory_fence import SecureMemoryFence
from xeren.security.network_guard import NetworkGuard
from xeren.security.schemas import (
    AccessDecision,
    AccessOutcome,
    DataSensitivityTier,
    UnlockChallenge,
)
from xeren.security.session_lock import SessionLockManager

logger = logging.getLogger("xeren.security.gate")


class XerenSecurityGate:
    """
    The 8-layer security gate that every Sensitive / More Sensitive data access
    must pass through.

    Layer 1: Intent Gate         — Does this request legitimately need this data?
    Layer 2: Classification      — Which tier? Liberal → fast path.
    Layer 3: Authentication Gate — Session unlock check.
    Layer 4: Path Containment    — WorkspacePermissionManager boundary.
    Layer 5: Decryption Gate     — Signal for caller to decrypt in-memory.
    Layer 6: Network Guard       — Block/restrict outbound operations.
    Layer 7: Memory Fence        — Signal caller to zero-fill after use.
    Layer 8: Audit Trail         — Log the access decision.
    """

    def __init__(
        self,
        classifier: Optional[DataClassifier] = None,
        session_lock: Optional[SessionLockManager] = None,
        network_guard: Optional[NetworkGuard] = None,
        audit_logger: Optional[SecurityAuditLogger] = None,
        memory_fence: Optional[SecureMemoryFence] = None,
        workspace_manager: Optional[Any] = None,
    ) -> None:
        self.classifier = classifier or DataClassifier()
        self.session_lock = session_lock  # Injected per session
        self.network_guard = network_guard or NetworkGuard()
        self.audit = audit_logger or SecurityAuditLogger()
        self.fence = memory_fence or SecureMemoryFence()
        self.workspace_manager = workspace_manager  # WorkspaceManager

    # ------------------------------------------------------------------
    # Main Entry Point
    # ------------------------------------------------------------------

    def check_access(
        self,
        path: Path,
        operation: str,
        user_id: str,
        user_intent: str = "",
        tier_override: Optional[DataSensitivityTier] = None,
    ) -> AccessDecision:
        """
        Run all 8 security layers for a data access request.

        Args:
            path: File or directory being accessed.
            operation: What operation (read, write, network, llm_prompt, etc.)
            user_id: The requesting user.
            user_intent: Natural language description of why access is needed.
            tier_override: Skip classification and use this tier directly.

        Returns:
            AccessDecision — caller must check .is_allowed before proceeding.
        """
        layers_passed: List[int] = []

        # ---- LAYER 1: Intent Gate ----------------------------------------
        # Verify there's a plausible legitimate reason for this access.
        # For now: non-empty intent or operation is sufficient.
        # Future: LLM-based intent verification.
        if not self._layer1_intent_check(user_intent, operation):
            decision = AccessDecision.denied(
                reason="No legitimate intent detected for this access request.",
                tier=DataSensitivityTier.LIBERAL,
            )
            self._audit(user_id, path, DataSensitivityTier.LIBERAL, operation, decision)
            return decision
        layers_passed.append(1)

        # ---- LAYER 2: Classification ----------------------------------------
        tier = tier_override or self.classifier.classify(path)
        layers_passed.append(2)

        # Liberal fast path — skip remaining layers
        if tier == DataSensitivityTier.LIBERAL:
            return AccessDecision.fast_path()

        # ---- LAYER 3: Authentication Gate ----------------------------------
        if not self._layer3_auth_check(tier):
            challenge = UnlockChallenge.pin_challenge(tier=tier, context=user_intent)
            decision = AccessDecision.needs_auth(challenge=challenge, tier=tier)
            self._audit(user_id, path, tier, operation, decision, layers_passed + [3])
            return decision
        layers_passed.append(3)

        # ---- LAYER 4: Path Containment -------------------------------------
        if not self._layer4_path_check(path):
            decision = AccessDecision.denied(
                reason="Path is outside all authorized workspace boundaries.",
                tier=tier,
            )
            self._audit(user_id, path, tier, operation, decision, layers_passed + [4])
            return decision
        layers_passed.append(4)

        # ---- LAYER 5: Decryption Gate --------------------------------------
        # We signal to the caller that they need to decrypt.
        # Actual decryption happens in WorkspaceContentRetriever, not here.
        layers_passed.append(5)

        # ---- LAYER 6: Network Guard ----------------------------------------
        net_allowed, net_reason = self.network_guard.validate_operation(tier, operation)
        if not net_allowed:
            decision = AccessDecision.denied(reason=net_reason, tier=tier)
            self._audit(user_id, path, tier, operation, decision, layers_passed + [6])
            return decision
        layers_passed.append(6)

        # ---- LAYER 7: Memory Fence ----------------------------------------
        # Signal to caller: fence must be used after processing.
        # No action here — the SecureMemoryFence context manager is used by caller.
        layers_passed.append(7)

        # ---- LAYER 8: Audit Trail -----------------------------------------
        decision = AccessDecision.allowed(tier=tier, layers=layers_passed + [8])
        self._audit(user_id, path, tier, operation, decision, layers_passed + [8])

        return decision

    # ------------------------------------------------------------------
    # Layer Implementations
    # ------------------------------------------------------------------

    def _layer1_intent_check(self, user_intent: str, operation: str) -> bool:
        """Layer 1: Basic intent plausibility check."""
        # Reject clearly empty / programmatic access with no context
        # A non-empty operation or intent is sufficient for now
        return bool(user_intent.strip() or operation.strip())

    def _layer3_auth_check(self, tier: DataSensitivityTier) -> bool:
        """Layer 3: Check if this tier is currently unlocked in the session."""
        if self.session_lock is None:
            # No session lock configured — default allow (dev mode)
            logger.warning(
                "SessionLockManager not configured — allowing access without auth check."
            )
            return True
        return self.session_lock.is_unlocked(tier)

    def _layer4_path_check(self, path: Path) -> bool:
        """Layer 4: Verify path is within an authorized workspace boundary."""
        if self.workspace_manager is None:
            return True  # No workspace manager — allow (permissive mode)
        try:
            # WorkspacePermissionManager.validate_path raises on violation
            permissions = getattr(self.workspace_manager, "permissions", None)
            if permissions is not None and hasattr(permissions, "validate_path"):
                permissions.validate_path(path, operation="read")
            return True
        except Exception:
            return False

    def _audit(
        self,
        user_id: str,
        path: Path,
        tier: DataSensitivityTier,
        operation: str,
        decision: AccessDecision,
        layers: Optional[List[int]] = None,
    ) -> None:
        """Layer 8: Write audit record."""
        if tier == DataSensitivityTier.LIBERAL:
            return  # Don't audit liberal — too verbose
        try:
            self.audit.log_access(
                user_id=user_id,
                path=str(path),
                tier=tier,
                operation=operation,
                outcome=decision.outcome,
                reason=decision.reason,
                layers_evaluated=layers or decision.layers_passed,
            )
        except Exception as exc:
            logger.error("Audit logging failed: %s", exc)

    # ------------------------------------------------------------------
    # Convenience: bulk reclassify (user moving data between tiers)
    # ------------------------------------------------------------------

    def reclassify(
        self,
        path: str,
        new_tier: DataSensitivityTier,
        user_id: str,
    ) -> None:
        """
        User reclassifies a file or folder into a different sensitivity tier.
        Override stored in DataClassifier and persisted via UserVault.
        """
        self.classifier.set_override(path, new_tier)
        logger.info(
            "User '%s' reclassified '%s' → %s",
            user_id, path, new_tier.value,
        )
        # Caller should persist override to UserVault
        self._audit(
            user_id=user_id,
            path=Path(path),
            tier=new_tier,
            operation="reclassify",
            decision=AccessDecision.allowed(tier=new_tier),
        )


__all__ = ["XerenSecurityGate"]
