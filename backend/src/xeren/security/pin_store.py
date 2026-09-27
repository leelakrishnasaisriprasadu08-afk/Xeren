"""PBKDF2-hashed PIN storage — PINs are never stored in plaintext."""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Optional

logger = logging.getLogger("xeren.security.pin_store")


class PinStore:
    """
    Secure PIN storage using PBKDF2-HMAC-SHA256.

    PINs are NEVER stored in plaintext.
    Each user has a unique salt — even the same PIN produces a different hash.
    Set once at onboarding. Changeable via verify + set flow.
    """

    # PBKDF2 iterations for PIN hashing — fast enough to verify, slow to brute-force
    _ITERATIONS = 300_000

    def __init__(self, db_path: str = "data/xeren.db") -> None:
        self._db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pin_store (
                    user_id TEXT PRIMARY KEY,
                    pin_hash TEXT NOT NULL,
                    salt     TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_pin(pin: str, salt: bytes) -> str:
        """Return hex-encoded PBKDF2-HMAC-SHA256 hash of the PIN."""
        dk = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=pin.encode("utf-8"),
            salt=salt,
            iterations=PinStore._ITERATIONS,
            dklen=32,
        )
        return dk.hex()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_pin(self, user_id: str) -> bool:
        """Return True if a PIN has been set for this user."""
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT 1 FROM pin_store WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def set_pin(self, user_id: str, pin: str) -> bool:
        """
        Hash and store a new PIN for the user.
        Safe to call at onboarding or after change_pin().
        """
        if len(pin.strip()) < 4:
            raise ValueError("PIN must be at least 4 characters.")

        import sqlite3
        from datetime import datetime, timezone

        salt = secrets.token_bytes(32)
        pin_hash = self._hash_pin(pin.strip(), salt)
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT INTO pin_store (user_id, pin_hash, salt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    pin_hash = excluded.pin_hash,
                    salt     = excluded.salt,
                    updated_at = excluded.updated_at
            """, (user_id, pin_hash, salt.hex(), now, now))
            conn.commit()
        finally:
            conn.close()

        logger.info("PIN set for user '%s'.", user_id)
        return True

    def verify_pin(self, user_id: str, candidate: str) -> bool:
        """
        Verify a candidate PIN against the stored hash.
        Returns True if correct, False otherwise.
        """
        import sqlite3

        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT pin_hash, salt FROM pin_store WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            logger.warning("No PIN found for user '%s'.", user_id)
            return False

        stored_hash, salt_hex = row
        salt = bytes.fromhex(salt_hex)
        candidate_hash = self._hash_pin(candidate.strip(), salt)

        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(stored_hash, candidate_hash)

    def change_pin(self, user_id: str, old_pin: str, new_pin: str) -> bool:
        """
        Change the PIN — requires the old PIN to be correct first.
        Returns True if changed, False if old_pin is wrong.
        """
        if not self.verify_pin(user_id, old_pin):
            logger.warning("PIN change failed for user '%s' — wrong current PIN.", user_id)
            return False
        self.set_pin(user_id, new_pin)
        logger.info("PIN changed for user '%s'.", user_id)
        return True

    def delete_pin(self, user_id: str) -> None:
        """Remove PIN record for a user (e.g. account deletion)."""
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("DELETE FROM pin_store WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()


__all__ = ["PinStore"]
