"""Tests for VerificationPlugin adapting outcome verification to BasePlugin."""

import pytest

from xeren.agent.plugins.verification import VerificationInput, VerificationOutput, VerificationPlugin
from xeren.data.schema import VerificationDetails
from xeren.plugins.manager import PluginManager


def test_verification_plugin_rules_and_syntax():
    """Verify VerificationPlugin validates artifacts and rules."""
    plugin = VerificationPlugin()

    # Case 1: Valid python code artifact and presence rule
    artifacts = {
        "code:solution.py": "def solve(): return 42",
        "doc:notes.txt": "Some research notes",
    }
    rules = ["exists:code:solution.py", "non_empty:doc:notes.txt"]

    details = plugin.verify_artifacts(task="Write solver", artifacts=artifacts, rules=rules)
    assert isinstance(details, VerificationDetails)
    assert details.verified is True
    assert details.score >= 0.8
    assert len(details.details["findings"]) >= 3


def test_verification_plugin_syntax_error_failure():
    """Verify VerificationPlugin detects syntax errors in code artifacts."""
    plugin = VerificationPlugin()
    artifacts = {"code:broken.py": "def invalid syntax : ((("}
    rules = ["exists:code:broken.py"]

    details = plugin.verify_artifacts(task="Broken code", artifacts=artifacts, rules=rules)
    assert details.verified is False
    assert any("Syntax error" in f for f in details.details["findings"])


def test_verification_plugin_plugin_manager_integration():
    """Verify VerificationPlugin runs through PluginManager."""
    pm = PluginManager()
    plugin = VerificationPlugin()
    pm.register(plugin)

    input_data = {
        "task": "Test verification",
        "artifacts": {"data:result.json": "{}"},
        "rules": ["exists:data:result.json"],
    }
    res = pm.execute("verification", input_data)

    assert res.success is True
    assert isinstance(res.output, VerificationOutput)
    assert res.output.details.verified is True
