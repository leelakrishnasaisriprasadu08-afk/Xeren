"""Authentication, HMAC verification, key rotation, and scope tests for ApiKeyManagerTool."""

from datetime import datetime, timedelta, timezone
import pytest

from xeren.plugins.api.schemas import ApiKeyEnvironment, ApiScope
from xeren.plugins.api.tools.auth import ApiKeyManagerTool
from xeren.plugins.api.tools.store import InMemoryApiKeyStore


def test_auth_generate_key():
    """Verify API key generation produces salted HMAC hash and returns plaintext key once."""
    store = InMemoryApiKeyStore()
    manager = ApiKeyManagerTool(store=store)

    meta, raw_key = manager.generate_key(
        name="Production Web Client",
        scopes=["research", "data"],
        rate_limit_per_minute=120,
        expires_in_days=30,
        environment=ApiKeyEnvironment.LIVE,
    )

    assert raw_key.startswith("xrn_live_")
    assert meta.prefix.startswith("xrn_live_")
    assert meta.name == "Production Web Client"
    assert meta.scopes == ["research", "data"]
    assert meta.rate_limit_per_minute == 120
    assert meta.expires_at is not None
    # Crucial security test: raw plaintext key is NOT stored in metadata
    assert raw_key != meta.key_hash
    assert raw_key not in meta.model_dump_json()

    # Saved in store
    retrieved = store.get_key(meta.key_id)
    assert retrieved is not None
    assert retrieved.name == "Production Web Client"


def test_auth_validate_key_success():
    """Verify authenticating a valid key succeeds in constant time."""
    manager = ApiKeyManagerTool()
    meta, raw_key = manager.generate_key(name="Valid Client", scopes=["coding"])

    is_valid, key_meta, err = manager.validate_key(raw_key)
    assert is_valid is True
    assert key_meta is not None
    assert key_meta.key_id == meta.key_id
    assert err is None
    # Verify last_used_at timestamp updated
    assert key_meta.last_used_at is not None


def test_auth_validate_invalid_format_and_secrets():
    """Verify bad formats and wrong secrets are rejected."""
    manager = ApiKeyManagerTool()
    _, raw_key = manager.generate_key(name="Client A")

    # Bad format
    valid, _, err = manager.validate_key("not_a_key")
    assert valid is False
    assert "Invalid API key format" in str(err)

    # Empty
    valid, _, err = manager.validate_key("")
    assert valid is False
    assert "Missing" in str(err)

    # Wrong secret token in valid-looking format
    tampered = raw_key[:-8] + "00000000"
    valid, _, err = manager.validate_key(tampered)
    assert valid is False
    assert "Invalid API key credentials" in str(err)


def test_auth_validate_expired_and_revoked():
    """Verify expired and revoked keys are rejected."""
    manager = ApiKeyManagerTool()
    meta, raw_key = manager.generate_key(name="Expiring Client")

    # Manually expire
    meta.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    manager.store.update_key(meta)

    valid, _, err = manager.validate_key(raw_key)
    assert valid is False
    assert "expired" in str(err).lower()

    # Reset expiration and revoke
    meta.expires_at = None
    meta.revoked_at = datetime.now(timezone.utc)
    manager.store.update_key(meta)

    valid, _, err = manager.validate_key(raw_key)
    assert valid is False
    assert "revoked" in str(err).lower()


def test_auth_rotate_key_immediate():
    """Verify immediate rotation revokes old key and provisions new active key."""
    manager = ApiKeyManagerTool()
    old_meta, old_raw = manager.generate_key(name="Key To Rotate", scopes=["website"])

    # Rotate with 0 grace period
    new_meta, new_raw = manager.rotate_key(old_meta.key_id, grace_period_seconds=0.0)

    assert new_raw != old_raw
    assert new_meta.key_id != old_meta.key_id
    assert new_meta.scopes == ["website"]

    # Old key immediately rejected
    valid_old, _, err_old = manager.validate_key(old_raw)
    assert valid_old is False
    assert "revoked" in str(err_old).lower()

    # New key accepted
    valid_new, _, err_new = manager.validate_key(new_raw)
    assert valid_new is True
    assert err_new is None


def test_auth_rotate_key_with_grace_period():
    """Verify rotation with grace period keeps old key temporarily active."""
    manager = ApiKeyManagerTool()
    old_meta, old_raw = manager.generate_key(name="Grace Key", scopes=["data"])

    # Rotate with 60s grace period
    new_meta, new_raw = manager.rotate_key(old_meta.key_id, grace_period_seconds=60.0)

    # Both keys valid during grace window
    valid_old, _, _ = manager.validate_key(old_raw)
    assert valid_old is True

    valid_new, _, _ = manager.validate_key(new_raw)
    assert valid_new is True


def test_auth_rotation_grace_period_lifecycle_requirements():
    """
    Verify the 6 core API-key rotation and grace-period requirements:
    1. Old key works before rotation.
    2. New key works immediately after rotation.
    3. Old key works during configured grace period.
    4. Old key fails after grace period.
    5. Explicitly revoked old key fails.
    6. Rotation without grace period invalidates the old key immediately.
    """
    manager = ApiKeyManagerTool()

    # --- Requirements 1, 2, 3, 4: Grace Period Lifecycle ---
    # 1. Old key works before rotation
    old_meta, old_raw = manager.generate_key(name="Lifecycle Client", scopes=["research", "coding"])
    valid_before, meta_before, err_before = manager.validate_key(old_raw)
    assert valid_before is True, "Requirement 1 failed: Old key must work before rotation"
    assert meta_before is not None
    assert err_before is None

    # Rotate with a configured grace period (60 seconds)
    new_meta, new_raw = manager.rotate_key(old_meta.key_id, grace_period_seconds=60.0)

    # 2. New key works immediately after rotation
    valid_new, meta_new, err_new = manager.validate_key(new_raw)
    assert valid_new is True, "Requirement 2 failed: New key must work immediately after rotation"
    assert meta_new is not None
    assert meta_new.key_id == new_meta.key_id
    assert err_new is None

    # 3. Old key works during configured grace period
    valid_during_grace, meta_during, err_during = manager.validate_key(old_raw)
    assert valid_during_grace is True, "Requirement 3 failed: Old key must work during grace period"
    assert meta_during is not None
    assert meta_during.key_id == old_meta.key_id
    assert err_during is None

    # 4. Old key fails after grace period
    # Simulate grace period expiration by shifting expires_at into the past
    retrieved_old = manager.store.get_key(old_meta.key_id)
    assert retrieved_old is not None
    retrieved_old.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    manager.store.update_key(retrieved_old)

    valid_after_grace, _, err_after = manager.validate_key(old_raw)
    assert valid_after_grace is False, "Requirement 4 failed: Old key must fail after grace period"
    assert err_after is not None
    assert "expired" in err_after.lower()

    # --- Requirement 5: Explicitly revoked old key fails immediately ---
    # Even during an active grace period, an explicitly revoked key must be rejected immediately
    key_for_revocation_meta, key_for_revocation_raw = manager.generate_key(name="Revoke During Grace Client")
    rotated_rev_meta, rotated_rev_raw = manager.rotate_key(
        key_for_revocation_meta.key_id, grace_period_seconds=3600.0
    )
    # Old key is valid in grace period
    valid_in_grace, _, _ = manager.validate_key(key_for_revocation_raw)
    assert valid_in_grace is True

    # Now explicitly revoke the old key
    revoked_ok = manager.revoke_key(key_for_revocation_meta.key_id, reason="Compromised credential")
    assert revoked_ok is True

    valid_revoked, _, err_revoked = manager.validate_key(key_for_revocation_raw)
    assert valid_revoked is False, "Requirement 5 failed: Explicitly revoked old key must fail immediately"
    assert err_revoked is not None
    assert "revoked" in err_revoked.lower()

    # The new replacement key remains active and unaffected
    valid_replacement, _, _ = manager.validate_key(rotated_rev_raw)
    assert valid_replacement is True

    # --- Requirement 6: Rotation without grace period invalidates old key immediately ---
    imm_old_meta, imm_old_raw = manager.generate_key(name="Immediate Rotation Client")
    imm_new_meta, imm_new_raw = manager.rotate_key(imm_old_meta.key_id, grace_period_seconds=0.0)

    valid_imm_old, _, err_imm_old = manager.validate_key(imm_old_raw)
    assert valid_imm_old is False, "Requirement 6 failed: Rotation without grace period must invalidate old key immediately"
    assert err_imm_old is not None
    assert "revoked" in err_imm_old.lower()

    valid_imm_new, _, err_imm_new = manager.validate_key(imm_new_raw)
    assert valid_imm_new is True, "Requirement 6 failed: New key must be active after immediate rotation"
    assert err_imm_new is None


def test_auth_revoke_key():
    """Verify explicit revocation disables key."""
    manager = ApiKeyManagerTool()
    meta, raw_key = manager.generate_key(name="Client to Revoke")

    revoked = manager.revoke_key(meta.key_id, reason="Security audit rotation")
    assert revoked is True

    valid, _, err = manager.validate_key(raw_key)
    assert valid is False
    assert "revoked" in str(err).lower()


def test_auth_scoped_permissions():
    """Verify fine-grained scope authorization."""
    manager = ApiKeyManagerTool()

    # Admin key (wildcard)
    admin_meta, _ = manager.generate_key(name="Admin", scopes=["*"])
    assert manager.has_permission(admin_meta, "research") is True
    assert manager.has_permission(admin_meta, "coding") is True
    assert manager.has_permission(admin_meta, "admin") is True

    # Dedicated admin keyword
    admin_kw_meta, _ = manager.generate_key(name="AdminKW", scopes=["admin"])
    assert manager.has_permission(admin_kw_meta, "website") is True

    # Domain-restricted key
    domain_meta, _ = manager.generate_key(name="ResearchOnly", scopes=["research", "knowledge"])
    assert manager.has_permission(domain_meta, "research") is True
    assert manager.has_permission(domain_meta, "knowledge") is True
    assert manager.has_permission(domain_meta, "coding") is False
    assert manager.has_permission(domain_meta, "admin") is False
