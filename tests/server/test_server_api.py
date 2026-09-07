"""Integration tests for FastAPI bridge server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from xeren.server.app import app

client = TestClient(app)


class TestServerAPI:
    def test_health_endpoint(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert "session_id" in data

    def test_dispatch_endpoint(self):
        resp = client.post("/api/dispatch", json={"query": "build a website for coffee roasters"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["plugin"] == "website"

    def test_security_tiers_endpoint(self):
        resp = client.get("/api/security/tiers")
        assert resp.status_code == 200
        data = resp.json()
        assert "liberal" in data
        assert "sensitive" in data
        assert "more_sensitive" in data

    def test_freelance_order_lifecycle(self):
        # 1. Ingest order
        create_resp = client.post("/api/workspaces/orders", json={
            "order_id": "TEST-FIVERR-001",
            "platform": "fiverr",
            "client_name": "Alice Green",
            "amount_usd": 300.0,
            "brief_prompt": "Create restaurant landing page with menu",
            "project_type": "website",
        })
        assert create_resp.status_code == 200
        assert create_resp.json()["status"] == "acknowledged"

        # 2. Check list
        list_resp = client.get("/api/workspaces")
        assert list_resp.status_code == 200
        orders = list_resp.json()["orders"]
        assert any(o["order_id"] == "TEST-FIVERR-001" for o in orders)

        # 3. Execute and deliver
        exec_resp = client.post("/api/workspaces/orders/TEST-FIVERR-001/execute")
        assert exec_resp.status_code == 200
        assert exec_resp.json()["success"] is True

    def test_strawberry_research_endpoint(self):
        resp = client.post("/api/research/strawberry", json={"topic": "Quantum Encryption Protocols", "depth": "deep"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["angles"]) >= 3
        assert data["safe_search_enforced"] is True

    def test_mcp_servers_and_tools(self):
        # 1. Get servers
        resp = client.get("/api/mcp/servers")
        assert resp.status_code == 200
        servers = resp.json()["servers"]
        assert len(servers) >= 6

        # 2. Get presets
        preset_resp = client.get("/api/mcp/presets")
        assert preset_resp.status_code == 200
        assert len(preset_resp.json()["presets"]) >= 6

        # 3. Call tool
        tool_resp = client.post(
            "/api/mcp/servers/filesystem/call-tool",
            json={"tool_name": "list_directory", "arguments": {"path": "./"}},
        )
        assert tool_resp.status_code == 200
        assert tool_resp.json()["success"] is True

        # 4. Toggle server
        toggle_resp = client.put("/api/mcp/servers/github/toggle", json={"enabled": False})
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["server"]["enabled"] is False

        # Re-enable for subsequent pipeline tests
        re_enable = client.put("/api/mcp/servers/github/toggle", json={"enabled": True})
        assert re_enable.status_code == 200
        assert re_enable.json()["server"]["enabled"] is True

    def test_mcp_pipeline_execution(self):
        # Execute cross-app interoperability pipeline
        resp = client.post("/api/mcp/pipelines/execute", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["step_results"]) > 0

    def test_user_account_login_and_logs(self):
        # 1. Get accounts list
        accts_resp = client.get("/api/accounts")
        assert accts_resp.status_code == 200
        accts = accts_resp.json()["accounts"]
        assert len(accts) >= 8

        # 2. Login on Gemini
        login_resp = client.post(
            "/api/accounts/login",
            json={
                "app_id": "gemini",
                "user_email": "leela@gmail.com",
                "user_name": "Leela User",
                "token_or_key": "AIzaSySecret123456",
                "plan_tier": "pro",
            },
        )
        assert login_resp.status_code == 200
        acct_data = login_resp.json()["account"]
        assert acct_data["auth_status"] == "authenticated"
        assert acct_data["user_email"] == "leela@gmail.com"
        assert "•••••••" in acct_data["masked_token"]

        # 3. Get logs and verify login event recorded
        logs_resp = client.get("/api/accounts/logs?app_id=gemini")
        assert logs_resp.status_code == 200
        logs = logs_resp.json()["logs"]
        assert len(logs) >= 1
        assert "leela@gmail.com" in logs[0]["message"]

        # 4. Logout
        logout_resp = client.post("/api/accounts/gemini/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["account"]["auth_status"] == "disconnected"

        # 5. Add custom app with URL, API key, and user details
        add_resp = client.post(
            "/api/accounts/add-custom",
            json={
                "app_name": "Private LLM Server",
                "category": "ai",
                "connection_type": "cloud_api",
                "endpoint_url": "https://api.privatellm.org/v1",
                "api_key_or_token": "sk-private-gateway-token-12345",
                "user_email": "admin@privatellm.org",
                "user_name": "Admin",
                "plan_tier": "enterprise",
            },
        )
        assert add_resp.status_code == 200
        custom_data = add_resp.json()["account"]
        assert custom_data["app_id"] == "private-llm-server"
        assert custom_data["endpoint_url"] == "https://api.privatellm.org/v1"
        assert custom_data["auth_status"] == "authenticated"
        assert "sk-•••••••2345" in custom_data["masked_token"]



