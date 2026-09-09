"""Tests for agent plugins: VerificationPlugin and ExperiencePlugin."""

import pytest

from xeren.agent.plugins import (
    ExperienceInput,
    ExperienceOutput,
    ExperiencePlugin,
    VerificationInput,
    VerificationOutput,
    VerificationPlugin,
)
from xeren.data.schema import DatasetSplit, ExperienceRecord, VerificationDetails
from xeren.eval.types import EvalSample
from xeren.plugins.contract import BasePlugin


def test_verification_plugin_execution():
    """Verify VerificationPlugin checks criteria and converts to VerificationDetails."""
    plugin = VerificationPlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "verification"

    # 1. Successful verification
    v_input = VerificationInput(
        task="Extract data from dashboard",
        success=True,
        expected_conditions=["not empty", "contains count"],
        actual_data={"count": 42, "items": ["a", "b"]},
    )
    result = plugin.execute(v_input)

    assert result.success is True
    assert isinstance(result.output, VerificationOutput)
    output = result.output
    assert output.verified is True
    assert output.score == 1.0

    details = output.to_verification_details()
    assert isinstance(details, VerificationDetails)
    assert details.verified is True

    # 2. Failed verification
    bad_input = VerificationInput(
        task="Check empty data",
        success=False,
        expected_conditions=["not empty"],
        actual_data={},
    )
    bad_result = plugin.execute(bad_input)
    assert isinstance(bad_result.output, VerificationOutput)
    assert bad_result.output.verified is False
    assert bad_result.output.score == 0.0


def test_experience_plugin_execution():
    """Verify ExperiencePlugin generates verified ExperienceRecords from agent trajectories."""
    plugin = ExperiencePlugin()
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "experience"

    simulated_state = {
        "task": "Navigate and download file",
        "plan": ["Navigate to example.com", "Download file"],
        "history": [
            [
                {"action_type": "navigate", "target": "https://example.com", "parameters": {}},
                {"success": True, "data": {"status": 200}},
            ],
            [
                {"action_type": "download", "target": "#download", "parameters": {}},
                {"success": True, "data": {"file_name": "data.csv"}},
            ],
        ],
    }

    exp_input = ExperienceInput(
        state=simulated_state,
        prediction_confidence=0.92,
        final_quality_score=0.98,
        split="train",
        verification_passed=True,
    )

    result = plugin.execute(exp_input)
    assert result.success is True
    assert isinstance(result.output, ExperienceOutput)
    output = result.output
    record = output.record

    assert isinstance(record, ExperienceRecord)
    assert record.task == "Navigate and download file"
    assert len(record.actions) == 2
    assert record.actions[0].tool_name == "navigate"
    assert record.actions[1].tool_name == "download"
    assert record.split == DatasetSplit.TRAIN
    assert record.is_verified is True
    assert output.fingerprint is not None
    assert len(output.fingerprint) == 64  # SHA-256

    # Convert to EvalSample to ensure evaluation framework integration
    eval_sample = record.to_eval_sample()
    assert isinstance(eval_sample, EvalSample)
    assert eval_sample.query == record.task
