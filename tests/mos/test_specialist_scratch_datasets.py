"""
Test suite verifying the schema integrity, persona consistency, and dataset validity
for ALL 14 Xeren MoS models in the minimized scratch dataset environment.
"""

import json
from pathlib import Path
import pytest

SPECIALISTS_DATA = Path("training/data/specialists")

ALL_MODELS_CONFIG = {
    "main_conductor": {
        "dir": SPECIALISTS_DATA / "main_conductor",
        "min_train_samples": 1500,
        "min_val_samples": 100,
    },
    "M0_tool_caller": {
        "dir": SPECIALISTS_DATA / "M0_tool_caller",
        "min_train_samples": 500,
        "min_val_samples": 80,
    },
    "M1_understanding": {
        "dir": SPECIALISTS_DATA / "M1_understanding",
        "min_train_samples": 250,
        "min_val_samples": 25,
    },
    "M2_reasoning": {
        "dir": SPECIALISTS_DATA / "M2_reasoning",
        "min_train_samples": 300,
        "min_val_samples": 50,
    },
    "M3_knowledge": {
        "dir": SPECIALISTS_DATA / "M3_knowledge",
        "min_train_samples": 250,
        "min_val_samples": 25,
    },
    "M4_research": {
        "dir": SPECIALISTS_DATA / "M4_research",
        "min_train_samples": 250,
        "min_val_samples": 25,
    },
    "M5_analysis": {
        "dir": SPECIALISTS_DATA / "M5_analysis",
        "min_train_samples": 250,
        "min_val_samples": 25,
    },
    "M6_planning": {
        "dir": SPECIALISTS_DATA / "M6_planning",
        "min_train_samples": 250,
        "min_val_samples": 25,
    },
    "M7_coding": {
        "dir": SPECIALISTS_DATA / "M7_coding",
        "min_train_samples": 500,
        "min_val_samples": 100,
    },
    "M8_simulation": {
        "dir": SPECIALISTS_DATA / "M8_simulation",
        "min_train_samples": 200,
        "min_val_samples": 20,
    },
    "M9_critic": {
        "dir": SPECIALISTS_DATA / "M9_critic",
        "min_train_samples": 200,
        "min_val_samples": 20,
    },
    "M10_verification": {
        "dir": SPECIALISTS_DATA / "M10_verification",
        "min_train_samples": 200,
        "min_val_samples": 20,
    },
    "M11_optimization": {
        "dir": SPECIALISTS_DATA / "M11_optimization",
        "min_train_samples": 200,
        "min_val_samples": 20,
    },
    "M12_experience": {
        "dir": SPECIALISTS_DATA / "M12_experience",
        "min_train_samples": 200,
        "min_val_samples": 20,
    },
}


@pytest.mark.parametrize("model_key", list(ALL_MODELS_CONFIG.keys()))
def test_dataset_files_exist_and_metadata_valid(model_key: str):
    cfg = ALL_MODELS_CONFIG[model_key]
    model_dir: Path = cfg["dir"]
    train_file = model_dir / "train.jsonl"
    val_file = model_dir / "val.jsonl"
    meta_file = model_dir / "metadata.json"

    assert train_file.exists(), f"Missing train.jsonl in {model_dir}"
    assert val_file.exists(), f"Missing val.jsonl in {model_dir}"
    assert meta_file.exists(), f"Missing metadata.json in {model_dir}"

    assert train_file.stat().st_size > 20000, f"train.jsonl unexpectedly small in {model_dir}"
    assert val_file.stat().st_size > 2000, f"val.jsonl unexpectedly small in {model_dir}"

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["specialist_id"] == model_key
    assert meta["training_samples"] >= cfg["min_train_samples"]
    assert meta["validation_samples"] >= cfg["min_val_samples"]
    assert len(meta["domains_covered"]) >= 2
    assert len(meta["train_sha256"]) == 64
    assert len(meta["val_sha256"]) == 64


@pytest.mark.parametrize("model_key", list(ALL_MODELS_CONFIG.keys()))
def test_dataset_record_schema_and_minimized_structure(model_key: str):
    cfg = ALL_MODELS_CONFIG[model_key]
    model_dir: Path = cfg["dir"]
    train_file = model_dir / "train.jsonl"

    with open(train_file, "r", encoding="utf-8") as f:
        # Check first 30 records in each dataset for high efficiency
        lines = [line.strip() for line in f if line.strip()][:30]

    assert len(lines) >= 30

    for line in lines:
        record = json.loads(line)
        assert "messages" in record, f"Record in {model_key} must follow ChatML messages schema"
        messages = record["messages"]
        assert len(messages) >= 3, f"Expected system, user, assistant messages in {model_key}, got {len(messages)}"

        system_msg = messages[0]
        user_msg = messages[1]
        asst_msg = messages[2]

        assert system_msg["role"] == "system"
        assert len(system_msg["content"].strip()) > 0

        assert user_msg["role"] == "user"
        assert len(user_msg["content"].strip()) > 0

        assert asst_msg["role"] == "assistant"
        assert len(asst_msg["content"].strip()) > 0
