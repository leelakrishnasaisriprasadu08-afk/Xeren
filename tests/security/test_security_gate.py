"""Tests for Xeren's 3-Tier Data Classification and 8-Layer Security Architecture."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from xeren.security.schemas import (
    DataSensitivityTier,
    AccessDecision,
    UnlockChallenge,
)
from xeren.security.classification import DataClassifier
from xeren.security.encryption import XerenEncryption
from xeren.security.pin_store import PinStore
from xeren.security.session_lock import SessionLockManager
from xeren.security.audit import SecurityAuditLogger
from xeren.security.memory_fence import SecureMemoryFence
from xeren.security.network_guard import NetworkGuard
from xeren.security.gate import XerenSecurityGate


class TestDataClassification:
    def test_liberal_classification(self):
        classifier = DataClassifier()
        assert classifier.classify("notes.txt") == DataSensitivityTier.LIBERAL
        assert classifier.classify("project/src/main.py") == DataSensitivityTier.LIBERAL
        assert classifier.classify("public_readme.md") == DataSensitivityTier.LIBERAL

    def test_sensitive_classification(self):
        classifier = DataClassifier()
        assert classifier.classify("vacation_photo.jpg") == DataSensitivityTier.SENSITIVE
        assert classifier.classify("family_video.mp4") == DataSensitivityTier.SENSITIVE
        assert classifier.classify("audio_recording.mp3") == DataSensitivityTier.SENSITIVE
        assert classifier.classify("personal/budget.xlsx") == DataSensitivityTier.SENSITIVE

    def test_more_sensitive_classification(self):
        classifier = DataClassifier()
        assert classifier.classify("aadhar_card.pdf") == DataSensitivityTier.MORE_SENSITIVE
        assert classifier.classify("passport_scan.png") == DataSensitivityTier.MORE_SENSITIVE
        assert classifier.classify("bank_statement.pdf") == DataSensitivityTier.MORE_SENSITIVE
        assert classifier.classify("private_key.pem") == DataSensitivityTier.MORE_SENSITIVE
        assert classifier.classify("secrets.env") == DataSensitivityTier.MORE_SENSITIVE
        assert classifier.classify("tax_return_2025.pdf") == DataSensitivityTier.MORE_SENSITIVE

    def test_user_override_precedence(self):
        classifier = DataClassifier()
        classifier.set_override("my_photo.jpg", DataSensitivityTier.MORE_SENSITIVE)
        assert classifier.classify("my_photo.jpg") == DataSensitivityTier.MORE_SENSITIVE

        classifier.set_override("sample_passport.pdf", DataSensitivityTier.LIBERAL)
        assert classifier.classify("sample_passport.pdf") == DataSensitivityTier.LIBERAL


class TestEncryption:
    def test_aes_gcm_encryption_decryption(self):
        engine = XerenEncryption()
        secret_data = b"Highly sensitive aadhar data: 1234-5678-9012"
        blob = engine.encrypt(secret_data, DataSensitivityTier.MORE_SENSITIVE, passphrase="master_password_123")
        assert blob.algorithm == "AES-256-GCM"
        assert blob.ciphertext != secret_data

        decrypted = engine.decrypt(blob, passphrase="master_password_123")
        assert decrypted == secret_data

    def test_aes_cbc_encryption_decryption(self):
        engine = XerenEncryption()
        sensitive_data = b"Personal photos binary stream"
        blob = engine.encrypt(sensitive_data, DataSensitivityTier.SENSITIVE, passphrase="master_password_123")
        assert blob.algorithm == "AES-256-CBC"

        decrypted = engine.decrypt(blob, passphrase="master_password_123")
        assert decrypted == sensitive_data


class TestPinStore:
    def test_pin_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pins.db"
            store = PinStore(db_path=db_path)
            user_id = "user_1"

            assert not store.has_pin(user_id)
            assert store.set_pin(user_id, "1234")
            assert store.has_pin(user_id)
            assert store.verify_pin(user_id, "1234")
            assert not store.verify_pin(user_id, "9999")


class TestSessionLock:
    def test_session_unlock_flow(self):
        manager = SessionLockManager(user_id="test_user_1")

        # Liberal is always unlocked
        assert manager.is_unlocked(DataSensitivityTier.LIBERAL)

        # Sensitive initially locked
        assert not manager.is_unlocked(DataSensitivityTier.SENSITIVE)

        # Unlock sensitive
        manager.unlock_tier(DataSensitivityTier.SENSITIVE)
        assert manager.is_unlocked(DataSensitivityTier.SENSITIVE)

        # Lock sensitive
        manager.lock_tier(DataSensitivityTier.SENSITIVE)
        assert not manager.is_unlocked(DataSensitivityTier.SENSITIVE)


class TestMemoryFence:
    def test_buffer_zeroing(self):
        fence = SecureMemoryFence()
        buf = bytearray(b"super_secret_credentials")
        fence.zero_buffer(buf)
        assert all(b == 0 for b in buf)

    def test_prompt_protection(self):
        fence = SecureMemoryFence()
        text = "Confidential business document content"
        sanitized_sensitive = fence.sanitize_for_llm(text, DataSensitivityTier.SENSITIVE)
        assert "Confidential business document content" not in sanitized_sensitive
        assert "SENSITIVE CONTENT" in sanitized_sensitive

        sanitized_more_sensitive = fence.sanitize_for_llm(text, DataSensitivityTier.MORE_SENSITIVE)
        assert "MORE SENSITIVE — content blocked" in sanitized_more_sensitive


class TestNetworkGuard:
    def test_network_isolation(self):
        guard = NetworkGuard()
        # More sensitive is hard-blocked from network transmission
        assert not guard.can_send_to_network(DataSensitivityTier.MORE_SENSITIVE)

        # Liberal and sensitive are allowed
        assert guard.can_send_to_network(DataSensitivityTier.LIBERAL)
        assert guard.can_send_to_network(DataSensitivityTier.SENSITIVE)

        # Validate operation check
        allowed, _ = guard.validate_operation(DataSensitivityTier.MORE_SENSITIVE, "network")
        assert not allowed

        allowed, _ = guard.validate_operation(DataSensitivityTier.LIBERAL, "network")
        assert allowed


class TestSecurityGate:
    def test_gate_evaluates_liberal_fast_path(self):
        gate = XerenSecurityGate()
        decision = gate.check_access(
            path=Path("docs/readme.txt"),
            operation="read",
            user_id="user_1",
            user_intent="reading documentation",
        )
        assert decision.is_allowed
        assert decision.tier == DataSensitivityTier.LIBERAL

    def test_gate_requires_auth_for_locked_sensitive(self):
        lock_mgr = SessionLockManager(user_id="user_1")
        gate = XerenSecurityGate(session_lock=lock_mgr)
        decision = gate.check_access(
            path=Path("photos/vacation.jpg"),
            operation="read",
            user_id="user_1",
            user_intent="viewing user photo",
        )
        assert decision.needs_auth
        assert decision.tier == DataSensitivityTier.SENSITIVE

    def test_gate_allows_when_tier_unlocked(self):
        lock_mgr = SessionLockManager(user_id="user_1")
        lock_mgr.unlock_tier(DataSensitivityTier.SENSITIVE)
        gate = XerenSecurityGate(session_lock=lock_mgr)
        decision = gate.check_access(
            path=Path("photos/vacation.jpg"),
            operation="read",
            user_id="user_1",
            user_intent="viewing user photo",
        )
        assert decision.is_allowed
        assert decision.tier == DataSensitivityTier.SENSITIVE
