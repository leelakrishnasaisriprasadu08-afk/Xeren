"""Unit and integration tests for PermittedDataHoldingVault."""

import tempfile
from pathlib import Path
import pytest

from xeren.core.data_holding import PermittedDataHoldingVault
from xeren.core.vault import UserVault
from xeren.security.schemas import DataSensitivityTier


@pytest.fixture
def temp_vault_env(tmp_path):
    vault_db = tmp_path / "test_vault.db"
    vault = UserVault(db_path=vault_db)
    holding_vault = PermittedDataHoldingVault(vault=vault)
    return vault, holding_vault, tmp_path


def test_hold_permitted_device_file(temp_vault_env):
    vault, holding_vault, tmp_path = temp_vault_env

    # 1. Create a directory and file
    allowed_dir = tmp_path / "allowed_project"
    allowed_dir.mkdir(parents=True, exist_ok=True)
    sample_file = allowed_dir / "architecture.md"
    sample_file.write_text("# Project Architecture\nUsing Xeren-Mini 1.5B with microservices.", encoding="utf-8")

    # 2. Before granting: should be rejected
    res_before = holding_vault.hold_device_file(sample_file, sample_file.read_text(encoding="utf-8"))
    assert res_before is None

    # 3. Grant directory access
    vault.grant_directory(allowed_dir, allow_write=True, description="Primary Project")

    # 4. Now holding should succeed
    item = holding_vault.hold_device_file(sample_file, sample_file.read_text(encoding="utf-8"))
    assert item is not None
    assert item.source_type == "device_file"
    assert item.title == "architecture.md"
    assert "1.5B" in item.content

    # 5. Check sync
    synced = holding_vault.sync_permitted_device_files()
    assert synced >= 1


def test_hold_connected_app_data(temp_vault_env):
    _, holding_vault, _ = temp_vault_env

    item = holding_vault.hold_connected_app_data(
        app_name="github",
        entity_id="issue_42",
        title="Fix model streaming delta latency",
        content="Issue description: Streaming tokens lag on slow connections. Proposed fix: buffer chunks.",
    )

    assert item.source_type == "connected_app"
    assert item.source_identifier == "github:issue_42"
    assert "[Github]" in item.title


def test_hold_web_research_and_context_prompt(temp_vault_env):
    _, holding_vault, _ = temp_vault_env

    holding_vault.hold_web_research(
        url="https://xeren.ai/docs/mini",
        title="Xeren-Mini 1.5B Parameter Model Guide",
        summary="Xeren-Mini is optimized for local edge deployment and fast planning.",
        evidence_snippets=["Runs at 45 tokens/sec on modern NPUs", "Uses rotary embeddings with 32k context"],
        credibility_score=0.98,
    )

    # Query held data
    matches = holding_vault.query_held_data("Xeren-Mini", limit=3)
    assert len(matches) > 0
    assert matches[0].source_type == "web_research"

    # Context prompt generation
    prompt = holding_vault.build_grounded_context_prompt("Xeren-Mini architecture")
    assert "[USER PERMITTED CONTEXT - GROUND TRUTH FROM DEVICE / APPS / WEB]" in prompt
    assert "Xeren-Mini" in prompt
