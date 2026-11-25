"""
test_triumvirate_api.py
=======================
Test suite for FastAPI endpoints exposing the Royal Triumvirate and Workstation Automator.
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from xeren.server.app import app

client = TestClient(app)


def test_triumvirate_api_deterministic_execution():
    """Verify POST /api/triumvirate/execute returns King, Advisor, and Commander data."""
    response = client.post(
        "/api/triumvirate/execute",
        json={"query": "show content of README.md"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    payload = data["data"]
    assert "README" in payload["final_response"] or "Xeren" in payload["final_response"]
    assert payload["deterministic_first_applied"] is True
    assert payload["advisor"] is not None
    assert payload["decree"] is not None
    assert payload["commander"] is not None
    assert len(payload["traces"]) >= 5


def test_triumvirate_api_hybrid_fallback():
    """Verify POST /api/triumvirate/execute triggers online fallback for heavy tasks."""
    response = client.post(
        "/api/triumvirate/execute",
        json={"query": "render 4k video animation scene"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    payload = data["data"]
    assert payload["hybrid_fallback_applied"] is True
    assert "remote web compute cluster" in payload["final_response"]

