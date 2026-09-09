"""Tests for tool-required routing signal detection and honest response boundaries."""

from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.conversation.schemas import (
    ConversationIntent,
    ConversationResult,
)


def test_routing_web_search() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": "Please search the web for the latest quantum computing papers"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.TOOL_REQUIRED
    assert output.routing.requires_tool is True
    assert output.routing.suggested_plugin == "research"
    # Never claim action was executed!
    assert "i have searched" not in output.response.lower()
    assert "i searched" not in output.response.lower()
    assert "found the following results" not in output.response.lower()
    assert "research" in output.response.lower()


def test_routing_code_generation() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": "Write a python script to parse JSON logs and write to SQLite"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.TOOL_REQUIRED
    assert output.routing.requires_tool is True
    assert output.routing.suggested_plugin == "coding"
    assert "i wrote the code" not in output.response.lower()
    assert "i created the script" not in output.response.lower()
    assert "coding" in output.response.lower()


def test_routing_website_creation() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": "Build a website for my digital photography portfolio"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.TOOL_REQUIRED
    assert output.routing.requires_tool is True
    assert output.routing.suggested_plugin == "website"
    assert "i have built" not in output.response.lower()
    assert "website" in output.response.lower()


def test_routing_data_analysis() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": "Analyze this dataset and plot a chart of monthly sales"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.TOOL_REQUIRED
    assert output.routing.requires_tool is True
    assert output.routing.suggested_plugin == "data"
    assert "i plotted" not in output.response.lower()
    assert "data" in output.response.lower()


def test_routing_file_operations() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": "Write to file report.txt with the meeting notes"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.TOOL_REQUIRED
    assert output.routing.requires_tool is True
    assert output.routing.suggested_plugin == "file"
    assert "i wrote to" not in output.response.lower()
    assert "file" in output.response.lower()


def test_routing_automation() -> None:
    plugin = ConversationPlugin()
    res = plugin.execute({"message": "Run the automation workflow for nightly backups"})
    assert res.success is True
    assert isinstance(res.output, ConversationResult)
    output = res.output
    assert output.intent == ConversationIntent.TOOL_REQUIRED
    assert output.routing.requires_tool is True
    assert output.routing.suggested_plugin == "automation"
    assert "i executed" not in output.response.lower()
    assert "automation" in output.response.lower()
