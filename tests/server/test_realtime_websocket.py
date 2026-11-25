"""Tests for the Realtime WebSocket gateway and Chat/Plan/Data-holding REST endpoints."""

import json
import pytest
from starlette.testclient import TestClient

from xeren.server.app import app, core, session, vault, data_holding


@pytest.fixture
def client():
    return TestClient(app)


def test_rest_chat_endpoint(client):
    # Test conversational chat
    res = client.post("/api/chat", json={"query": "Hello Xeren, how do you manage autonomous plans?"})
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    assert data.get("verified") is True


def test_rest_task_planning_and_proceed_flow(client):
    # 1. Ask for a website task -> should stage a plan
    res_stage = client.post("/api/chat", json={"query": "Build a responsive modern website for my creative agency"})
    assert res_stage.status_code == 200
    stage_data = res_stage.json()
    assert stage_data["type"] == "plan_staged"
    assert "proceed to the plan" in stage_data["content"]

    # 2. Check /api/plan/active
    res_active = client.get("/api/plan/active")
    assert res_active.status_code == 200
    active_data = res_active.json()
    assert active_data["staged"] is True
    assert active_data["status"] == "staged"

    # 3. Explicitly trigger proceed
    res_proceed = client.post("/api/plan/proceed")
    assert res_proceed.status_code == 200
    proceed_data = res_proceed.json()
    assert proceed_data["success"] is True
    assert "Task Plan Executed Successfully" in proceed_data["deliverable"]

    # 4. Active plan should now be cleared
    res_cleared = client.get("/api/plan/active")
    assert res_cleared.json()["staged"] is False


def test_rest_data_holding_endpoints(client, tmp_path):
    # 1. Grant and hold directory
    test_dir = tmp_path / "held_docs"
    test_dir.mkdir()
    doc = test_dir / "guide.md"
    doc.write_text("Xeren-Mini 1.5B edge agent instructions.", encoding="utf-8")

    grant_res = client.post("/api/data-holding/grant-and-hold", json={
        "directory_path": str(test_dir.resolve()),
        "description": "Guides folder"
    })
    assert grant_res.status_code == 200
    assert grant_res.json()["success"] is True

    # 2. List held items
    list_res = client.get("/api/data-holding")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(i["title"] == "guide.md" for i in items)

    # 3. Query held data
    query_res = client.post("/api/data-holding/query", json={"query": "Xeren-Mini", "limit": 3})
    assert query_res.status_code == 200
    assert len(query_res.json()["matches"]) > 0


def test_websocket_realtime_communication(client):
    with client.websocket_connect("/api/v1/realtime") as ws:
        # 1. Receive initial conversation start event
        init_event = ws.receive_json()
        assert init_event["type"] == "conversation.start"

        # 2. Send user query
        ws.send_json({
            "type": "user.text",
            "text": "What are your core autonomous capabilities?",
        })

        # 3. Expect response.created
        created_event = ws.receive_json()
        assert created_event["type"] == "response.created"

        # 4. Expect streaming deltas and response.complete
        received_deltas = []
        received_complete = False

        # Read events until response.complete
        for _ in range(50):
            msg = ws.receive_json()
            if msg["type"] == "response.text.delta":
                received_deltas.append(msg["delta"])
            elif msg["type"] == "response.text.complete":
                received_complete = True
                break

        assert received_complete is True
        assert len(received_deltas) > 0
