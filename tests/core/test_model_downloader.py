"""
test_model_downloader.py
========================
Test suite for the Triumvirate model weight downloader and auto-discovery engine.
"""

import json
import tempfile
import pytest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.download_triumvirate_models import (
    MODEL_CATALOG,
    check_disk_space,
    generate_manifest,
    get_model_status,
)
from xeren.runtime.local_runner import LocalMultiModelRuntime


def test_check_disk_space():
    """Verify that disk space calculation accurately checks drive free space."""
    target_path = Path("models/triumvirate")
    ok, free_gb, req_gb = check_disk_space(target_path, 1000) # 1 GB
    assert isinstance(ok, bool)
    assert free_gb > 0
    assert req_gb == 0.98


def test_get_model_status_and_manifest_generation():
    """Verify that catalog statuses are accurately assessed and manifest is written."""
    manifest_path = generate_manifest(MODEL_CATALOG)
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["manifest_version"] == "1.0.0"
    assert data["total_models"] == 3
    assert data["estimated_vram_concurrent_gb"] == 3.65
    assert "king" in data["models"]
    assert "advisor" in data["models"]
    assert "commander" in data["models"]


def test_runtime_auto_discovers_manifest():
    """Verify that LocalMultiModelRuntime reads manifest and auto-populates paths."""
    runtime = LocalMultiModelRuntime()
    # The King should have discovered the existing HF checkpoint on disk
    assert runtime.king_config.model_name == "Xeren-Sovereign-1.5B"
    assert runtime.king_config.model_path is not None
    assert "xeren_mini_final" in runtime.king_config.model_path

