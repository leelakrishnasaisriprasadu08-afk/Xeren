"""Unit tests for Project Coach Agent, Role Assignment, and Isolated Workstation Sessions."""

import pytest
from fastapi.testclient import TestClient

from xeren.server.app import app
from xeren.projects.schemas import ProjectRole, ProjectSpecification


@pytest.fixture
def client():
    return TestClient(app)


def test_isolated_coach_history(client):
    """Test that member coaching histories are strictly segregated per workstation session."""
    # Dev user history
    dev_resp = client.get("/api/projects/proj_cyberforge_group/coach/messages?member_id=usr_dev_01")
    assert dev_resp.status_code == 200
    dev_msgs = dev_resp.json()["messages"]
    assert len(dev_msgs) >= 1
    assert dev_msgs[0]["member_user_id"] == "usr_dev_01"

    # Sarah history
    sarah_resp = client.get("/api/projects/proj_cyberforge_group/coach/messages?member_id=usr_peer_02")
    assert sarah_resp.status_code == 200
    sarah_msgs = sarah_resp.json()["messages"]
    assert len(sarah_msgs) >= 1
    assert sarah_msgs[0]["member_user_id"] == "usr_peer_02"
    assert "AI Specialist" in sarah_msgs[0]["content"]

    # Ensure message sets are completely disjoint
    dev_ids = {m["message_id"] for m in dev_msgs}
    sarah_ids = {m["message_id"] for m in sarah_msgs}
    assert dev_ids.isdisjoint(sarah_ids)


def test_zero_interruption_parallel_coaching(client):
    """Test that simultaneous questions from different members receive isolated replies without cross-bleeding."""
    # 1. Dev user asks about architecture
    dev_chat_resp = client.post(
        "/api/projects/proj_cyberforge_group/coach/chat",
        json={
            "project_id": "proj_cyberforge_group",
            "member_user_id": "usr_dev_01",
            "message": "What is our architecture pattern and system constraints?",
            "role_context": "architect",
        },
    )
    assert dev_chat_resp.status_code == 200
    dev_reply = dev_chat_resp.json()["message"]
    assert "Architecture Guidance" in dev_reply["content"]
    assert "Distributed Multi-Agent Event Bus" in dev_reply["content"]

    # 2. Sarah asks about her role and AI benchmarks at the same time
    sarah_chat_resp = client.post(
        "/api/projects/proj_cyberforge_group/coach/chat",
        json={
            "project_id": "proj_cyberforge_group",
            "member_user_id": "usr_peer_02",
            "message": "What is my role responsibility for AI specialist?",
            "role_context": "ai_specialist",
        },
    )
    assert sarah_chat_resp.status_code == 200
    sarah_reply = sarah_chat_resp.json()["message"]
    assert "Role Focus: Ai Specialist" in sarah_reply["content"]
    assert "usr_peer_02" == sarah_reply["member_user_id"]

    # Verify Sarah's message did not pollute Dev user's message stream
    dev_stream_after = client.get("/api/projects/proj_cyberforge_group/coach/messages?member_id=usr_dev_01").json()["messages"]
    for msg in dev_stream_after:
        assert msg["member_user_id"] == "usr_dev_01"
        assert "What is my role responsibility" not in msg["content"]


def test_update_project_specifications(client):
    """Test updating technical specifications and engineering constraints."""
    update_resp = client.put(
        "/api/projects/proj_cyberforge_group/specifications",
        json={
            "specifications": {
                "tech_stack": ["TypeScript", "FastAPI", "MongoDB Atlas", "React 19", "WebSockets", "Docker"],
                "architecture_pattern": "Hybrid Event-Driven Microservices",
                "constraints": [
                    "Zero-interruption workstation isolation",
                    "Deterministic state synchronization",
                    "Real-time sync latency < 35ms",
                ],
                "target_apis": ["OpenAI API", "Anthropic Claude API", "Gemini Pro API", "MongoDB Atlas", "Redis"],
                "deliverables": [
                    "Parallel collaborative workstations",
                    "AI Coach integration",
                    "Role matrix management",
                    "Containerized orchestration deploy",
                ],
            }
        },
    )
    assert update_resp.status_code == 200
    project = update_resp.json()["project"]
    specs = project["specifications"]
    assert "Docker" in specs["tech_stack"]
    assert specs["architecture_pattern"] == "Hybrid Event-Driven Microservices"
    assert "Redis" in specs["target_apis"]


def test_update_member_role_and_responsibilities(client):
    """Test assigning a new role and active task to a project member."""
    role_resp = client.put(
        "/api/projects/proj_cyberforge_group/members/usr_peer_02/role",
        json={
            "role": "tech_lead",
            "active_task": "Reviewing security architecture and API contracts",
        },
    )
    assert role_resp.status_code == 200
    project = role_resp.json()["project"]
    sarah_member = next(m for m in project["members"] if m["user_id"] == "usr_peer_02")
    assert sarah_member["role"] == "tech_lead"
    assert sarah_member["active_task"] == "Reviewing security architecture and API contracts"


def test_workstation_heartbeat(client):
    """Test updating workstation heartbeat and active task status."""
    hb_resp = client.post(
        "/api/projects/proj_cyberforge_group/workstations/heartbeat",
        json={
            "member_user_id": "usr_dev_01",
            "active_task": "Profiling WebSocket multiplexer latency",
            "status": "active",
        },
    )
    assert hb_resp.status_code == 200
    ws = hb_resp.json()["workstation"]
    assert ws["member_user_id"] == "usr_dev_01"
    assert ws["active_task"] == "Profiling WebSocket multiplexer latency"
    assert ws["status"] == "active"
