"""
test_desktop_copilot.py
=======================
Test suite for the frontline DesktopCopilot and workstation automation.
"""

import pytest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from xeren.copilot.desktop_copilot import DesktopCopilot, CopilotTurnResult


def test_copilot_single_command_deterministic():
    """Verify that DesktopCopilot executes a deterministic command and formats output."""
    copilot = DesktopCopilot()
    turn = copilot.execute_command("show content of README.md")

    assert isinstance(turn, CopilotTurnResult)
    assert len(turn.response) > 0
    assert turn.runtime_result.deterministic_first_applied is True
    
    formatted = copilot.format_turn(turn, verbose=True)
    assert "👑 XEREN SOVEREIGN" in formatted
    assert "⚡ Deterministic Fast-Path" in formatted
    assert "Total Latency:" in formatted


def test_copilot_hybrid_fallback_execution():
    """Verify that heavy commands trigger the Hybrid Fallback Gateway in Copilot."""
    copilot = DesktopCopilot()
    turn = copilot.execute_command("render 4k video animation scene")

    assert turn.runtime_result.hybrid_fallback_applied is True
    formatted = copilot.format_turn(turn, verbose=True)
    assert "🌐 Hybrid Fallback Gateway" in formatted


def test_copilot_interactive_history():
    """Verify that multiple turns are preserved in Copilot history."""
    copilot = DesktopCopilot()
    copilot.execute_command("list files in current directory")
    copilot.execute_command("show system specs and cpu info")

    assert len(copilot.history) == 2
    assert "list" in copilot.history[0].query
    assert "system" in copilot.history[1].query

