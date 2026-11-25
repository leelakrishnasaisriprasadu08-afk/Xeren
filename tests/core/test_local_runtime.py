"""
test_local_runtime.py
=====================
Test suite for the unified LocalMultiModelRuntime and inter-model communication bus.
"""

import pytest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from xeren.runtime.local_runner import (
    LocalMultiModelRuntime,
    InterModelBus,
    ModelSlotConfig,
    RuntimeExecutionResult,
)


def test_inter_model_bus_latency():
    """Verify that inter-model in-memory handoffs are sub-5ms."""
    bus = InterModelBus()
    payload = {"task": "verify_files", "priority": "high"}
    
    _, trace = bus.dispatch("KING", "ADVISOR", "COUNSEL_REQUEST", payload)
    
    assert trace.sender == "KING"
    assert trace.receiver == "ADVISOR"
    assert trace.latency_ms < 5.0 # Must be sub-5ms for in-memory queues
    assert trace.payload_size_bytes > 0


def test_local_runtime_standard_task():
    """Test full Triumvirate loop on an OS/Files task."""
    runtime = LocalMultiModelRuntime()
    result = runtime.process("show content of README.md")
    
    assert isinstance(result, RuntimeExecutionResult)
    assert result.advisor_counsel is not None
    assert result.royal_decree is not None
    assert result.commander_report is not None
    assert result.commander_report.success is True
    assert len(result.final_response) > 0
    assert result.deterministic_first_applied is True
    assert len(result.traces) >= 5 # USER->KING, KING->ADV, ADV->KING, KING->COMM, COMM->KING, KING->USER


def test_local_runtime_hybrid_fallback():
    """Test that heavy non-laptop tasks trigger the Hybrid Fallback Gateway."""
    runtime = LocalMultiModelRuntime()
    result = runtime.process("render 4k video animation scene")
    
    assert result.advisor_counsel is not None
    assert result.commander_report is not None
    assert result.commander_report.success is True
    assert result.hybrid_fallback_applied is True
    assert any("Online" in b.get("bot_id", "") for b in result.bot_executions)


def test_local_runtime_agentic_task():
    """Test standard agentic task dispatches to micro-bot."""
    runtime = LocalMultiModelRuntime()
    result = runtime.process("Design a responsive navigation bar in Tailwind CSS")
    
    assert result.advisor_counsel is not None
    assert result.commander_report is not None
    assert result.commander_report.success is True
    assert len(result.final_response) > 0
