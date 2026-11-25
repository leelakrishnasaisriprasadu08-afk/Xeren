"""
Test suite verifying the AST and schema integrity of the manufactured M7 Coding dataset.
"""

import ast
import json
from pathlib import Path
import re
import pytest

from automation_framework.mos.specialist_registry import SpecialistID, SpecialistRegistry

DATA_DIR = Path("training/data/specialists/M7_coding")
TRAIN_FILE = DATA_DIR / "train.jsonl"
VAL_FILE = DATA_DIR / "val.jsonl"
META_FILE = DATA_DIR / "metadata.json"


def test_dataset_files_exist_and_non_empty():
    assert TRAIN_FILE.exists(), f"Missing train file: {TRAIN_FILE}"
    assert VAL_FILE.exists(), f"Missing val file: {VAL_FILE}"
    assert META_FILE.exists(), f"Missing metadata file: {META_FILE}"

    assert TRAIN_FILE.stat().st_size > 100000, "Train dataset size unexpectedly small"
    assert VAL_FILE.stat().st_size > 20000, "Val dataset size unexpectedly small"


def test_metadata_integrity():
    with open(META_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["specialist_id"] == "M7_coding"
    assert meta["ast_validation_pass_rate"] == 1.0
    assert meta["training_samples"] >= 500
    assert meta["validation_samples"] >= 100
    assert "algorithms" in meta["domains_covered"]
    assert "systems" in meta["domains_covered"]
    assert "architecture" in meta["domains_covered"]
    assert "testing" in meta["domains_covered"]
    assert "refactoring" in meta["domains_covered"]
    assert "ai_math" in meta["domains_covered"]


@pytest.mark.parametrize("split_path", [TRAIN_FILE, VAL_FILE])
def test_dataset_record_schema_and_ast_integrity(split_path: Path):
    with open(split_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) > 0

    for rec in records:
        messages = rec.get("messages", [])
        assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
        system_msg, user_msg, assistant_msg = messages

        assert system_msg["role"] == "system"
        assert "M7 Coding" in system_msg["content"]

        assert user_msg["role"] == "user"
        assert len(user_msg["content"].strip()) > 0

        assert assistant_msg["role"] == "assistant"
        content = assistant_msg["content"]

        # Must contain code block
        match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
        assert match is not None, "Assistant content missing ```python ... ``` fence"

        code_snippet = match.group(1)
        # Parse through Python AST
        try:
            parsed = ast.parse(code_snippet)
            assert parsed is not None
        except SyntaxError as e:
            pytest.fail(f"AST syntax error in sample: {e}\nSnippet:\n{code_snippet}")


def test_specialist_registry_m7_coding():
    spec = SpecialistRegistry.get(SpecialistID.CODING)
    assert spec is not None
    assert spec.id == SpecialistID.CODING
    assert spec.enabled is True
    assert "code" in spec.capabilities
    assert "implement" in spec.capabilities
    assert "m7_coding" in spec.checkpoint_dir


@pytest.mark.asyncio
async def test_specialist_runner_native_m7_coding():
    from automation_framework.mos.protocol import SpecialistTask, TaskStatus
    from automation_framework.mos.specialist_runner import SpecialistRunner

    runner = SpecialistRunner()
    task = SpecialistTask(
        trace_id="test-m7-native",
        specialist_id="M7_coding",
        specialist_name="M7 — Coding / Creation",
        sub_task="Implement a Python function to compute factorial",
        max_tokens=20,
    )
    res = await runner.run(task)
    assert res.status == TaskStatus.SUCCESS
    assert res.confidence == 1.0  # Confirms NATIVE execution mode

