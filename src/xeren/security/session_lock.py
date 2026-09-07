"""Once-per-session unlock state manager — authenticate once, stay unlocked silently."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from xeren.security.schemas import AuthMethod, DataSensitivityTier, UnlockChallenge

logger = logging.getLogger("xeren.security.session_lock")

# Session inactivity timeouts per tier
_TIMEOUT_MINUTES: dict[DataSensitivityTier, int] = {
    DataSensitivityTier.LIBERAL: 0,           # Never needs auth
    DataSensitivityTier.SENSITIVE: 30,         # Lock after 30min inactivity
    DataSensitivityTier.MORE_SENSITIVE: 10,    # Lock after 10min inactivity
}


class _TierLockState:
    """Internal state for one tier's unlock status."""

    def __init__(self, timeout_minutes: int) -> None:
        self._unlocked: bool = False
        self._unlocked_at: Optional[datetime] = None
        self._last_accessed: Optional[datetime] = None
        self._timeout = timedelta(minutes=timeout_minutes)

    def is_unlocked(self) -> bool:
        if not self._unlocked:
            return False
        now = datetime.now(timezone.utc)
        last = self._last_accessed or self._unlocked_at
        if last and (now - last) > self._timeout:
            # Timed out — silently re-lock
            self._unlocked = False
            logger.debug("Tier auto-locked due to inactivity.")
            return False
        # Touch last accessed time
        self._last_accessed = now
        return True

    def unlock(self) -> None:
        self._unlocked = True
        self._unlocked_at = datetime.now(timezone.utc)
        self._last_accessed = datetime.now(timezone.utc)

    def lock(self) -> None:
        self._unlocked = False
        self._unlocked_at = None
        self._last_accessed = None


class SessionLockManager:
    """
    Manages tier unlock state per session.

    Design rules:
    - Liberal: always unlocked, never asks for auth.
    - Sensitive: ask ONCE per session, then silent for 30min inactivity.
    - More Sensitive: ask ONCE per session, silent for 10min inactivity.

    After timeout, one quiet re-verification is needed.
    Never shows repeated prompts within the activity window.
    """

    def __init__(self, user_id: str, pin_store: Optional[object] = None) -> None:
        self.user_id = user_id
        self._pin_store = pin_store

        self._states: dict[DataSensitivityTier, _TierLockState] = {
            DataSensitivityTier.LIBERAL: _TierLockState(timeout_minutes=0),
            DataSensitivityTier.SENSITIVE: _TierLockState(
                timeout_minutes=_TIMEOUT_MINUTES[DataSensitivityTier.SENSITIVE]
            ),
            DataSensitivityTier.MORE_SENSITIVE: _TierLockState(
                timeout_minutes=_TIMEOUT_MINUTES[DataSensitivityTier.MORE_SENSITIVE]
            ),
        }
        # Liberal is always unlocked
        self._states[DataSensitivityTier.LIBERAL].unlock()

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------

    def is_unlocked(self, tier: DataSensitivityTier) -> bool:
        """Return True if this tier is currently accessible without re-auth."""
        return self._states[tier].is_unlocked()

    def needs_auth(self, tier: DataSensitivityTier) -> bool:
        """Return True if the user must authenticate to access this tier."""
        return tier != DataSensitivityTier.LIBERAL and not self.is_unlocked(tier)

    # ------------------------------------------------------------------
    # Challenge Generation
    # ------------------------------------------------------------------

    def get_challenge(self, tier: DataSensitivityTier, context: str = "") -> UnlockChallenge:
        """
        Generate the unlock challenge to show the user.
        Called by XerenSecurityGate when auth is needed.
        """
        return UnlockChallenge.pin_challenge(tier=tier, context=context)

    # ------------------------------------------------------------------
    # Verification + Unlock
    # ------------------------------------------------------------------

    def verify_and_unlock(self, tier: DataSensitivityTier, pin: str) -> bool:
        """
        Verify PIN and unlock tier if correct.

        Args:
            tier: The sensitivity tier to unlock.
            pin: The user's PIN input.

        Returns:
            True if verification succeeded and tier is now unlocked.
        """
        if tier == DataSensitivityTier.LIBERAL:
            return True  # Always unlocked

        if self._pin_store is None:
            logger.warning("No PinStore configured — cannot verify PIN.")
            return False

        verified = self._pin_store.verify_pin(self.user_id, pin)
        if verified:
            self._states[tier].unlock()
            logger.info(
                "Tier '%s' unlocked for user '%s'.", tier.value, self.user_id
            )
        else:
            logger.warning(
                "PIN verification failed for tier '%s', user '%s'.",
                tier.value, self.user_id,
            )
        return verified

    def unlock_tier(self, tier: DataSensitivityTier) -> None:
        """Directly unlock a tier (e.g. after valid authentication or in test harness)."""
        self._states[tier].unlock()
        logger.info("Tier '%s' unlocked for user '%s'.", tier.value, self.user_id)

    # ------------------------------------------------------------------
    # Manual Lock (e.g. user explicitly locks)
    # ------------------------------------------------------------------

    def lock_tier(self, tier: DataSensitivityTier) -> None:
        """Manually lock a tier (e.g. user goes idle, or explicitly locks)."""
        self._states[tier].lock()
        logger.info("Tier '%s' manually locked for user '%s'.", tier.value, self.user_id)

    def lock_all(self) -> None:
        """Lock all tiers — called on session end."""
        for tier in [DataSensitivityTier.SENSITIVE, DataSensitivityTier.MORE_SENSITIVE]:
            self._states[tier].lock()
        logger.info("All tiers locked for user '%s' (session end).", self.user_id)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict[str, bool]:
        """Return unlock status for all tiers — for debugging / health check."""
        return {
            tier.value: self._states[tier].is_unlocked()
            for tier in DataSensitivityTier
        }


__all__ = ["SessionLockManager"]
