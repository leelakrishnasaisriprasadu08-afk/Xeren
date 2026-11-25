"""Unit tests for UserVault, XerenSession, IntentClassifier, and XerenDispatcher."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from xeren.core.vault import UserVault
from xeren.core.session import XerenSession
from xeren.core.intent import IntentClassifier, IntentResult
from xeren.core.dispatcher import XerenDispatcher
from xeren.security.schemas import DataSensitivityTier
from xeren.security.pin_store import PinStore


class TestUserVault:
    def test_directory_grant_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vault.db"
            vault = UserVault(db_path=db_path)

            folder_to_grant = Path(tmpdir) / "my_projects"
            folder_to_grant.mkdir()

            assert not vault.is_directory_granted(folder_to_grant)
            vault.grant_directory(folder_to_grant, allow_write=True, description="Coding workspace")
            assert vault.is_directory_granted(folder_to_grant)

            subfile = folder_to_grant / "src" / "main.py"
            assert vault.is_directory_granted(subfile)

            vault.revoke_directory(folder_to_grant)
            assert not vault.is_directory_granted(folder_to_grant)

    def test_encrypted_account_credentials(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vault.db"
            vault = UserVault(db_path=db_path, encryption_key="super_secret_test_key")

            creds = {"api_token": "fiverr_tok_xyz123", "seller_id": "freelancer_pro"}
            vault.store_account_credentials("fiverr_main", "fiverr", creds)

            retrieved = vault.get_account_credentials("fiverr_main")
            assert retrieved == creds
            assert vault.get_account_credentials("non_existent") is None

    def test_tier_overrides_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vault.db"
            vault = UserVault(db_path=db_path)

            vault.set_tier_override("photos/vacation.jpg", DataSensitivityTier.MORE_SENSITIVE)
            overrides = vault.get_all_tier_overrides()
            assert overrides["photos/vacation.jpg"] == DataSensitivityTier.MORE_SENSITIVE


class TestIntentClassifier:
    def test_freelance_platform_intent(self):
        classifier = IntentClassifier()
        res = classifier.classify("handle my fiverr account and check new client orders")
        assert res.plugin == "automation"
        assert res.action == "freelance_platform"
        assert res.entities.get("platform") == "fiverr"

        res_upwork = classifier.classify("draft a proposal for this upwork job post")
        assert res_upwork.plugin == "automation"
        assert res_upwork.entities.get("platform") == "upwork"

    def test_website_creation_intent(self):
        classifier = IntentClassifier()
        res = classifier.classify("build a website for an artisan bakery with dark mode")
        assert res.plugin == "website"
        assert res.action == "generate_website"

    def test_coding_intent(self):
        classifier = IntentClassifier()
        res = classifier.classify("write a python function to parse json logs and test it")
        assert res.plugin == "coding"
        assert res.action == "write_code"

    def test_deep_research_intent(self):
        classifier = IntentClassifier()
        res = classifier.classify("deep search about latest quantum computing breakthroughs")
        assert res.plugin == "research"
        assert res.action == "deep_research"


class TestDispatcher:
    def test_auto_dispatch_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vault.db"
            pin_db = Path(tmpdir) / "pins.db"
            vault = UserVault(db_path=db_path)
            pin_store = PinStore(db_path=pin_db)
            session = XerenSession(vault=vault, pin_store=pin_store)

            dispatcher = XerenDispatcher(session=session)
            resp = dispatcher.dispatch("build a website for my portfolio")
            assert resp.plugin_name == "website"
            assert resp.success
