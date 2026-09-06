"""API key generation, secure HMAC hashing, verification, rotation, and scoped permission authority."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import secrets
from typing import Any, Dict, List, Optional, Tuple

from xeren.plugins.api.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyEnvironment,
    ApiKeyMetadata,
    ApiScope,
)
from xeren.plugins.api.tools.store import BaseApiKeyStore, InMemoryApiKeyStore

logger = logging.getLogger("xeren.plugins.api.tools.auth")


class ApiKeyManagerTool:
    """Security authority managing Xeren API key lifecycles, HMAC verification, and scopes.
    
    KEY ARCHITECTURE:
    - Format: `xrn_{env}_{id_prefix}_{secret_token}`
      Example: `xrn_live_a1b2c3d4_8f9e0d1c2b3a4e5f6...`
    - Security: The raw secret token is hashed using HMAC-SHA256 with a per-key cryptographic salt.
    - Zero Plaintext Storage: Only the salted HMAC hash, prefix, and metadata are saved.
    - Constant-time validation: Employs `hmac.compare_digest` to prevent timing side-channel attacks.
    """

    def __init__(self, store: Optional[BaseApiKeyStore] = None) -> None:
        self.store = store or InMemoryApiKeyStore()

    def generate_key(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        rate_limit_per_minute: int = 60,
        expires_in_days: Optional[int] = None,
        environment: ApiKeyEnvironment = ApiKeyEnvironment.LIVE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ApiKeyMetadata, str]:
        """
        Generate a new cryptographically secure Xeren API key.
        
        Returns:
            Tuple of (ApiKeyMetadata, raw_plaintext_key).
            WARNING: The plaintext key MUST be returned to the client immediately and NEVER saved.
        """
        env_str = environment.value
        id_prefix = secrets.token_hex(4)  # 8 hex characters
        secret_part = secrets.token_hex(24)  # 48 hex characters
        raw_key = f"xrn_{env_str}_{id_prefix}_{secret_part}"

        salt = secrets.token_hex(16)
        key_hash = self._compute_hash(raw_key, salt)
        key_id = f"key_{id_prefix}_{secrets.token_hex(4)}"

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

        granted_scopes = scopes or [ApiScope.ALL.value]
        # Normalize scopes
        granted_scopes = [s.strip().lower() for s in granted_scopes if s.strip()]

        key_meta = ApiKeyMetadata(
            key_id=key_id,
            name=name,
            prefix=f"xrn_{env_str}_{id_prefix}...",
            key_hash=key_hash,
            salt=salt,
            scopes=granted_scopes,
            rate_limit_per_minute=rate_limit_per_minute,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        self.store.save_key(key_meta)
        logger.info("Generated API key '%s' with prefix '%s'", name, key_meta.prefix)
        return key_meta, raw_key

    def validate_key(
        self, raw_key: Optional[str]
    ) -> Tuple[bool, Optional[ApiKeyMetadata], Optional[str]]:
        """
        Authenticate an incoming raw API key against the persistent store.

        Returns:
            (is_valid, key_metadata, error_message)
        """
        if not raw_key or not isinstance(raw_key, str):
            return False, None, "Missing API key"

        raw_key = raw_key.strip()
        parts = raw_key.split("_")
        # Expected: xrn, env, id_prefix, secret
        if len(parts) != 4 or parts[0] != "xrn":
            return False, None, "Invalid API key format"

        id_prefix = parts[2]
        # Search by key_id prefix or lookup via store
        candidate_meta = None
        for key in self.store.list_keys(include_revoked=True):
            if key.key_id.startswith(f"key_{id_prefix}_"):
                candidate_meta = key
                break

        if not candidate_meta:
            return False, None, "API key not recognized"

        # Verify HMAC hash using constant-time comparison
        computed_hash = self._compute_hash(raw_key, candidate_meta.salt)
        if not hmac.compare_digest(computed_hash, candidate_meta.key_hash):
            return False, None, "Invalid API key credentials"

        # Check revocation
        if candidate_meta.revoked_at is not None:
            return False, candidate_meta, "API key has been revoked"

        # Check expiration
        now = datetime.now(timezone.utc)
        if candidate_meta.expires_at is not None and now > candidate_meta.expires_at:
            return False, candidate_meta, "API key has expired"

        # Update last_used_at timestamp
        candidate_meta.last_used_at = now
        self.store.update_key(candidate_meta)

        return True, candidate_meta, None

    def rotate_key(
        self,
        key_id: str,
        grace_period_seconds: float = 0.0,
    ) -> Tuple[ApiKeyMetadata, str]:
        """
        Rotate an active API key, generating a replacement with identical scopes and limits.
        
        If grace_period_seconds == 0, the old key is revoked immediately.
        If grace_period_seconds > 0, the old key will expire after the grace window.
        """
        old_meta = self.store.get_key(key_id)
        if not old_meta:
            raise ValueError(f"API key '{key_id}' not found.")

        now = datetime.now(timezone.utc)
        if grace_period_seconds <= 0.0:
            old_meta.revoked_at = now
            old_meta.metadata["rotation_reason"] = "immediate_rotation"
        else:
            old_meta.expires_at = now + timedelta(seconds=grace_period_seconds)
            old_meta.metadata["rotation_grace_period_seconds"] = grace_period_seconds
        self.store.update_key(old_meta)

        # Generate replacement key with same scopes, name, and rate limit
        new_meta, new_raw_key = self.generate_key(
            name=f"{old_meta.name} (Rotated)",
            scopes=old_meta.scopes,
            rate_limit_per_minute=old_meta.rate_limit_per_minute,
            environment=ApiKeyEnvironment.LIVE if "live" in old_meta.prefix else ApiKeyEnvironment.TEST,
            metadata={"rotated_from": old_meta.key_id, **old_meta.metadata},
        )
        logger.info("Rotated key '%s' into new key '%s'", key_id, new_meta.key_id)
        return new_meta, new_raw_key

    def revoke_key(self, key_id: str, reason: Optional[str] = None) -> bool:
        """Revoke an active key immediately, preventing any further usage."""
        meta = self.store.get_key(key_id)
        if not meta:
            return False

        meta.revoked_at = datetime.now(timezone.utc)
        if reason:
            meta.metadata["revocation_reason"] = reason
        self.store.update_key(meta)
        logger.info("Revoked API key '%s' (reason: %s)", key_id, reason)
        return True

    def has_permission(self, key_meta: ApiKeyMetadata, required_scope: str) -> bool:
        """
        Check if the key possesses the required scope or admin privilege.
        
        Supported scopes:
        - `*` or `admin`: Superuser access to all routes.
        - Domain scopes: `research`, `knowledge`, `coding`, `website`, `data`, `file`,
          `verification`, `experience`, `automation`, `health`.
        """
        if not key_meta.is_active:
            return False

        scopes_lower = [s.lower() for s in key_meta.scopes]
        if "*" in scopes_lower or "admin" in scopes_lower:
            return True

        req_lower = required_scope.strip().lower()
        return req_lower in scopes_lower

    @staticmethod
    def _compute_hash(raw_key: str, salt: str) -> str:
        """Compute salted HMAC-SHA256 digest of raw key."""
        return hmac.new(
            salt.encode("utf-8"), raw_key.encode("utf-8"), hashlib.sha256
        ).hexdigest()


__all__ = ["ApiKeyManagerTool"]
