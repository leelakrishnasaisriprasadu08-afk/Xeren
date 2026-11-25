"""Test suite verifying the AST and schema integrity of the manufactured ToolCaller dataset."""

import ast
import json
from pathlib import Path
import pytest

DATA_DIR = Path("training/data/specialists/M0_tool_caller")
TRAIN_FILE = DATA_DIR / "train.jsonl"
VAL_FILE = DATA_DIR / "val.jsonl"


def test_dataset_files_exist_and_non_empty():
    assert TRAIN_FILE.exists(), f"Missing train file: {TRAIN_FILE}"
    assert VAL_FILE.exists(), f"Missing val file: {VAL_FILE}"
    assert TRAIN_FILE.stat().st_size > 100000, "Train dataset size unexpectedly small"
    assert VAL_FILE.stat().st_size > 20000, "Val dataset size unexpectedly small"


@pytest.mark.parametrize("split_path", [TRAIN_FILE, VAL_FILE])
def test_dataset_record_schema_and_ast_integrity(split_path: Path):
    with open(split_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) > 0

    for rec in records:
        messages = rec.get("messages", [])
        assert len(messages) == 3
        system_msg, user_msg, assistant_msg = messages

        assert system_msg["role"] == "system"
        assert user_msg["role"] == "user"
        assert assistant_msg["role"] == "assistant"

        # Assistant payload must be valid JSON
        payload = json.loads(assistant_msg["content"])
        assert "phase" in payload
        assert "confidence" in payload
        assert 0.0 <= payload["confidence"] <= 1.0

        if payload["phase"] == "assign":
            assert "assignments" in payload
            assert isinstance(payload["assignments"], list)
            for assign in payload["assignments"]:
                assert "specialist_id" in assign
                assert "action" in assign
                assert "arguments" in assign
                assert "expectation" in assign
        elif payload["phase"] == "verify":
            assert "passed" in payload
            assert "syntax_valid" in payload
            assert "needs_retry" in payload
            assert isinstance(payload["passed"], bool)
            assert isinstance(payload["syntax_valid"], bool)
            assert isinstance(payload["needs_retry"], bool)
