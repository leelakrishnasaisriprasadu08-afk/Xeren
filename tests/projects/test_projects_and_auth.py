"""Unit tests for Projects, Multi-Member Collaboration, Multi-Method Auth, and MongoDB."""

import pytest
from fastapi.testclient import TestClient

from xeren.server.app import app
from xeren.auth.schemas import AuthMethod
from xeren.projects.schemas import ProjectType, ProjectRole, InviteType, InviteStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_system_version_and_db_status(client):
    """Test system version handshake and MongoDB status reporting."""
    resp = client.get("/api/system/version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["backend_version"] == "1.2.0"
    assert data["protocol_version"] == "v2.strawberry"
    assert "database" in data
    assert "active_user" in data

    db_resp = client.get("/api/db/status")
    assert db_resp.status_code == 200
    db_data = db_resp.json()
    assert "mode" in db_data
    assert "collections" in db_data


def test_auth_me_and_social_login(client):
    """Test retrieving user profile and social login (Google, GitHub, Facebook)."""
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    user = me_resp.json()["user"]
    assert user["handle"] == "@xeren_dev"
    assert "google" in user["linked_methods"] or "passkey" in user["linked_methods"]

    # Test Facebook Social Auth
    fb_resp = client.post(
        "/api/auth/social",
        json={
            "provider": "facebook",
            "token_or_code": "mock_fb_access_token_81723",
            "name": "Alex FB Mercer",
            "email": "alex.mercer@meta-developer.net",
        },
    )
    assert fb_resp.status_code == 200
    updated_user = fb_resp.json()["user"]
    assert "facebook" in updated_user["linked_methods"]


def test_passkey_registration_and_verification(client):
    """Test WebAuthn / FIDO2 Passkey device registration and unlock."""
    reg_resp = client.post(
        "/api/auth/passkey/register",
        json={
            "device_name": "YubiKey 5C NFC",
            "credential_id": "cred_yubi_99812",
            "public_key": "p256_mock_public_key_bytes_12345",
        },
    )
    assert reg_resp.status_code == 200
    user = reg_resp.json()["user"]
    assert any(p["credential_id"] == "cred_yubi_99812" for p in user["passkeys"])

    # Test verification
    verify_resp = client.post(
        "/api/auth/passkey/verify",
        json={"credential_id": "cred_yubi_99812"},
    )
    assert verify_resp.status_code == 200


def test_otp_send_and_verify(client):
    """Test 6-digit OTP code dispatch to email and phone number."""
    # 1. Email OTP
    send_resp = client.post(
        "/api/auth/otp/send",
        json={"target": "colleague@xeren.ai", "method": "email"},
    )
    assert send_resp.status_code == 200
    otp_data = send_resp.json()
    code = otp_data["code_preview"]
    assert len(code) == 6

    verify_resp = client.post(
        "/api/auth/otp/verify",
        json={"target": "colleague@xeren.ai", "code": code, "method": "email"},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["success"] is True

    # 2. Phone OTP
    phone_send = client.post(
        "/api/auth/otp/send",
        json={"target": "+15551234567", "method": "phone"},
    )
    assert phone_send.status_code == 200
    phone_code = phone_send.json()["code_preview"]
    assert len(phone_code) == 6

    phone_verify = client.post(
        "/api/auth/otp/verify",
        json={"target": "+15551234567", "code": phone_code, "method": "phone"},
    )
    assert phone_verify.status_code == 200


def test_solo_and_group_project_creation(client):
    """Test creating Solo project and Group collaborative project."""
    # 1. Solo Project
    solo_resp = client.post(
        "/api/projects/create",
        json={
            "name": "Quantum Solitary Analysis",
            "description": "Deep single-user research session",
            "project_type": "solo",
            "tags": ["quantum", "offline"],
        },
    )
    assert solo_resp.status_code == 200
    solo_proj = solo_resp.json()["project"]
    assert solo_proj["project_type"] == "solo"
    assert len(solo_proj["members"]) == 1
    assert solo_proj["members"][0]["is_owner"] is True

    # 2. Group Project with initial members
    group_resp = client.post(
        "/api/projects/create",
        json={
            "name": "Mesh Swarm Alpha",
            "description": "Collaborative neural network workspace",
            "project_type": "group",
            "tags": ["mesh", "swarm"],
            "initial_invites": [
                {
                    "project_id": "",
                    "invite_type": "xeren_account",
                    "target": "@sarah_ai",
                    "role": "editor",
                },
                {
                    "project_id": "",
                    "invite_type": "email",
                    "target": "external_dev@partner.com",
                    "role": "viewer",
                },
            ],
        },
    )
    assert group_resp.status_code == 200
    group_proj = group_resp.json()["project"]
    assert group_proj["project_type"] == "group"
    assert len(group_proj["invites"]) == 2

    # Check that in-app and email invites were created properly
    inv_xeren = next(i for i in group_proj["invites"] if i["invite_type"] == "xeren_account")
    inv_email = next(i for i in group_proj["invites"] if i["invite_type"] == "email")
    assert inv_xeren["recipient"] == "@sarah_ai"
    assert inv_xeren["mail_dispatch_status"] == "in_app_notification_delivered"
    assert inv_email["recipient"] == "external_dev@partner.com"
    assert inv_email["mail_dispatch_status"] == "verification_email_dispatched"
    assert len(inv_email["verification_code"]) == 6


def test_invite_acceptance_and_join_by_code(client):
    """Test accepting in-app invite and joining via email verification code."""
    # Create group project
    create_resp = client.post(
        "/api/projects/create",
        json={
            "name": "Neural Nexus Team",
            "project_type": "group",
        },
    )
    proj_id = create_resp.json()["project"]["project_id"]

    # Dispatch invite to @sarah_ai
    inv_resp = client.post(
        "/api/projects/invite",
        json={
            "project_id": proj_id,
            "invite_type": "xeren_account",
            "target": "@sarah_ai",
            "role": "editor",
        },
    )
    assert inv_resp.status_code == 200
    invite_id = inv_resp.json()["invite"]["invite_id"]
    code = inv_resp.json()["invite"]["verification_code"]

    # Accept invite
    accept_resp = client.post(f"/api/projects/invites/{invite_id}/accept")
    assert accept_resp.status_code == 200
    updated_proj = accept_resp.json()["project"]
    assert any(m["handle"] == "@xeren_dev" for m in updated_proj["members"])

    # Create email invite and join via code
    email_inv = client.post(
        "/api/projects/invite",
        json={
            "project_id": proj_id,
            "invite_type": "email",
            "target": "alice@remote.org",
            "role": "reviewer",
        },
    )
    email_code = email_inv.json()["invite"]["verification_code"]

    # Join using 6-digit code
    join_resp = client.post(
        "/api/projects/join-code",
        json={"code_or_token": email_code},
    )
    assert join_resp.status_code == 200
