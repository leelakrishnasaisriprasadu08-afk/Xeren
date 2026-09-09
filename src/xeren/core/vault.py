"""UserVault — Persistent one-time directory grants, account secrets, and user overrides."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from xeren.security.schemas import DataSensitivityTier
from xeren.security.encryption import XerenEncryption

logger = logging.getLogger("xeren.core.vault")


class UserVault:
    """
    Encrypted, persistent storage for user-granted permissions,
    account credentials (Fiverr, Upwork, etc.), and file tier overrides.

    Ensures the user is only asked for permissions ONCE, after which
    Xeren accesses authorized directories directly.
    """

    def __init__(self, db_path: Optional[Path] = None, encryption_key: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = Path.home() / ".xeren" / "vault"
            data_dir.mkdir(parents=True, exist_ok=True)
            self._db_path = data_dir / "user_vault.db"
        else:
            self._db_path = Path(db_path)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._encryption_key = encryption_key or "default_xeren_local_vault_key"
        self._encryption = XerenEncryption()
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS directory_grants (
                    path TEXT PRIMARY KEY,
                    granted_at TEXT NOT NULL,
                    allow_write INTEGER NOT NULL DEFAULT 1,
                    description TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tier_overrides (
                    path TEXT PRIMARY KEY,
                    tier TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS account_credentials (
                    account_name TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    encrypted_data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Directory Grants (One-Time Permission System)
    # ------------------------------------------------------------------

    def grant_directory(self, path: str | Path, allow_write: bool = True, description: str = "") -> None:
        """Grant persistent one-time access to a directory."""
        normalized = Path(path).resolve().as_posix()
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT INTO directory_grants (path, granted_at, allow_write, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    allow_write = excluded.allow_write,
                    description = excluded.description
            """, (normalized, now, 1 if allow_write else 0, description))
            conn.commit()
            logger.info("Persistent access granted to: %s", normalized)
        finally:
            conn.close()

    def revoke_directory(self, path: str | Path) -> bool:
        """Revoke previously granted directory access."""
        normalized = Path(path).resolve().as_posix()
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("DELETE FROM directory_grants WHERE path = ?", (normalized,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def is_directory_granted(self, path: str | Path) -> bool:
        """Check if a path falls inside any approved directory grant."""
        normalized = Path(path).resolve().as_posix().lower()
        grants = self.get_all_granted_directories()
        for grant in grants:
            grant_norm = Path(grant["path"]).resolve().as_posix().lower()
            if normalized == grant_norm or normalized.startswith(grant_norm + "/"):
                return True
        return False

    def get_all_granted_directories(self) -> List[Dict[str, Any]]:
        """List all directories with permanent access grants."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM directory_grants ORDER BY granted_at DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Data Sensitivity Overrides
    # ------------------------------------------------------------------

    def set_tier_override(self, path: str | Path, tier: DataSensitivityTier) -> None:
        """Persist a user override moving a file/folder to another sensitivity block."""
        normalized = Path(path).as_posix().lower()
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT INTO tier_overrides (path, tier, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    tier = excluded.tier,
                    updated_at = excluded.updated_at
            """, (normalized, tier.value, now))
            conn.commit()
            logger.info("Tier override saved: %s -> %s", normalized, tier.value)
        finally:
            conn.close()

    def get_all_tier_overrides(self) -> Dict[str, DataSensitivityTier]:
        """Load all saved overrides for DataClassifier."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("SELECT path, tier FROM tier_overrides")
            overrides = {}
            for path, tier_str in cursor.fetchall():
                try:
                    overrides[path] = DataSensitivityTier(tier_str)
                except ValueError:
                    continue
            return overrides
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Account Credentials (Encrypted)
    # ------------------------------------------------------------------

    def store_account_credentials(self, account_name: str, platform: str, credentials: Dict[str, Any]) -> None:
        """Encrypt and store credentials for Fiverr, Upwork, Telegram, etc."""
        raw_bytes = json.dumps(credentials).encode("utf-8")
        encrypted_blob = self._encryption.encrypt(
            data=raw_bytes,
            tier=DataSensitivityTier.MORE_SENSITIVE,
            passphrase=self._encryption_key,
        )
        payload = json.dumps(encrypted_blob.to_dict())
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT INTO account_credentials (account_name, platform, encrypted_data, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_name) DO UPDATE SET
                    platform = excluded.platform,
                    encrypted_data = excluded.encrypted_data,
                    updated_at = excluded.updated_at
            """, (account_name, platform, payload, now))
            conn.commit()
            logger.info("Encrypted credentials saved for account '%s' on %s", account_name, platform)
        finally:
            conn.close()

    def get_account_credentials(self, account_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt account credentials."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "SELECT encrypted_data FROM account_credentials WHERE account_name = ?",
                (account_name,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            data_dict = json.loads(row[0])
            from xeren.security.schemas import EncryptedBlob
            blob = EncryptedBlob.from_dict(data_dict)
            decrypted_bytes = self._encryption.decrypt(blob, passphrase=self._encryption_key)
            return json.loads(decrypted_bytes.decode("utf-8"))
        finally:
            conn.close()

    def list_accounts(self) -> List[Dict[str, str]]:
        """List stored account names and platforms without revealing credentials."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("SELECT account_name, platform, updated_at FROM account_credentials")
            return [{"account_name": r[0], "platform": r[1], "updated_at": r[2]} for r in cursor.fetchall()]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # User Preferences
    # ------------------------------------------------------------------

    def set_preference(self, key: str, value: Any) -> None:
        """Set user configuration preference."""
        val_str = json.dumps(value)
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, val_str, now))
            conn.commit()
        finally:
            conn.close()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user configuration preference."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return default
            return json.loads(row[0])
        finally:
            conn.close()


__all__ = ["UserVault"]
