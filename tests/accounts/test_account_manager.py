"""Unit tests for AccountManager and User App Authentication."""

import pytest
from xeren.accounts.manager import AccountManager
from xeren.accounts.schemas import AccountAuthStatus, AccountLoginRequest, AccountPlanTier, AppEventType
from xeren.core.vault import UserVault


def test_account_manager_default_catalog(tmp_path):
    vault = UserVault(db_path=tmp_path / "test_vault.db")
    mgr = AccountManager(vault=vault)
    accounts = mgr.list_accounts()
    assert len(accounts) >= 16

    app_ids = [a.app_id for a in accounts]
    assert "gemini" in app_ids
    assert "canva" in app_ids
    assert "huggingface" in app_ids
    assert "openai" in app_ids
    assert "perplexity" in app_ids
    assert "midjourney" in app_ids
    assert "supabase" in app_ids
    assert "gdrive" in app_ids
    assert "discord" in app_ids
    assert "spotify" in app_ids
    assert "linear" in app_ids


def test_account_manager_login_and_logout(tmp_path):
    vault = UserVault(db_path=tmp_path / "test_vault.db")
    mgr = AccountManager(vault=vault)

    # 1. Login with user account details on Gemini
    req = AccountLoginRequest(
        app_id="gemini",
        user_email="leela@gmail.com",
        user_name="Leela",
        token_or_key="AIzaSyA1234567890abcdef",
        plan_tier=AccountPlanTier.PRO,
    )
    acct = mgr.login_account(req)

    assert acct.auth_status == AccountAuthStatus.AUTHENTICATED
    assert acct.user_email == "leela@gmail.com"
    assert acct.user_name == "Leela"
    assert "•••••••" in acct.masked_token

    # Verify credentials stored in vault
    creds = vault.get_account_credentials("user_app_gemini")
    assert creds is not None
    assert creds["user_email"] == "leela@gmail.com"
    assert creds["token"] == "AIzaSyA1234567890abcdef"

    # Verify activity log event generated
    logs = mgr.get_logs(app_id="gemini")
    assert len(logs) >= 1
    assert "leela@gmail.com" in logs[0].message

    # 2. Logout
    out_acct = mgr.logout_account("gemini")
    assert out_acct.auth_status == AccountAuthStatus.DISCONNECTED
    assert out_acct.user_email is None


def test_account_manager_activity_logs(tmp_path):
    vault = UserVault(db_path=tmp_path / "test_vault.db")
    mgr = AccountManager(vault=vault)

    # Log custom app event
    mgr.log_event(
        app_id="canva",
        app_name="Canva Design",
        user_email="designer@studio.com",
        event_type=AppEventType.TOOL_CALL,
        message="Exported 4K marketing graphic via Canva Connect API",
    )

    canva_logs = mgr.get_logs(app_id="canva")
    assert len(canva_logs) == 1
    assert canva_logs[0].event_type == AppEventType.TOOL_CALL
    assert "Canva Connect API" in canva_logs[0].message


def test_account_manager_local_device_apps_without_api_key(tmp_path):
    """Test native desktop applications (Blender, VS Code, OBS) link without an API key."""
    from xeren.accounts.schemas import AddLocalAppRequest

    vault = UserVault(db_path=tmp_path / "test_vault.db")
    mgr = AccountManager(vault=vault)

    # 1. Verify Blender 3D is in catalog with requires_api_key=False
    blender = mgr.get_account("blender")
    assert blender is not None
    assert blender.app_name == "Blender 3D"
    assert blender.requires_api_key is False
    assert blender.connection_type == "local_device"
    assert blender.local_path == "blender"

    # 2. Link Blender without an API key
    req = AccountLoginRequest(
        app_id="blender",
        user_email="device@xeren.local",
        user_name="3D Artist",
        token_or_key="",  # No API key
        local_path="C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
        connection_type="local_device",
    )
    linked = mgr.login_account(req)
    assert linked.auth_status == AccountAuthStatus.AUTHENTICATED
    assert linked.local_path == "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe"
    assert "local:" in linked.masked_token

    # Verify audit log reflects local linking without API key
    logs = mgr.get_logs(app_id="blender")
    assert len(logs) >= 1
    assert "No API key required" in logs[0].message

    # 3. Register custom local device app (e.g. Godot Engine)
    custom_req = AddLocalAppRequest(
        app_name="Godot Engine",
        category="design",
        local_path="C:\\Tools\\godot.exe",
        description="Local 2D/3D open-source game engine",
        capabilities=["game-export", "gdscript-automation"],
    )
    custom_app = mgr.add_local_device_app(custom_req)
    assert custom_app.app_id == "godot-engine"
    assert custom_app.requires_api_key is False
    assert custom_app.connection_type == "local_device"
    assert custom_app.auth_status == AccountAuthStatus.AUTHENTICATED
    assert custom_app.local_path == "C:\\Tools\\godot.exe"

    # Verify custom app is in list_accounts
    all_accts = mgr.list_accounts()
    assert any(a.app_id == "godot-engine" for a in all_accts)


def test_account_manager_add_custom_app_with_url_key_and_user_details(tmp_path):
    """Test registering a custom web API / service with URL, API key, and user details."""
    from xeren.accounts.schemas import AddCustomAppRequest

    vault = UserVault(db_path=tmp_path / "test_vault.db")
    mgr = AccountManager(vault=vault)

    req = AddCustomAppRequest(
        app_name="Ollama Private Server",
        category="ai",
        connection_type="cloud_api",
        endpoint_url="http://localhost:11434/v1",
        api_key_or_token="sk-custom-ollama-secret-998877",
        user_email="researcher@local.ai",
        user_name="Leela Researcher",
        plan_tier=AccountPlanTier.ENTERPRISE,
        description="Local private inference gateway with custom Llama-3 models",
        capabilities=["custom-llm", "local-embeddings"],
    )
    acct = mgr.add_custom_app(req)

    assert acct.app_id == "ollama-private-server"
    assert acct.app_name == "Ollama Private Server"
    assert acct.endpoint_url == "http://localhost:11434/v1"
    assert acct.user_email == "researcher@local.ai"
    assert acct.user_name == "Leela Researcher"
    assert acct.plan_tier == AccountPlanTier.ENTERPRISE
    assert acct.auth_status == AccountAuthStatus.AUTHENTICATED
    assert "sk-•••••••8877" in acct.masked_token
    assert acct.is_custom is True

    # Verify credentials stored encrypted in UserVault
    creds = vault.get_account_credentials("user_app_ollama-private-server")
    assert creds is not None
    assert creds["token"] == "sk-custom-ollama-secret-998877"
    assert creds["endpoint_url"] == "http://localhost:11434/v1"
    assert creds["user_email"] == "researcher@local.ai"

    # Verify audit log recorded
    logs = mgr.get_logs(app_id="ollama-private-server")
    assert len(logs) == 1
    assert "http://localhost:11434/v1" in logs[0].message
    assert "researcher@local.ai" in logs[0].message


