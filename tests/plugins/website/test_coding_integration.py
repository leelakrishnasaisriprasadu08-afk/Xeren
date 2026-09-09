"""Tests verifying Website Plugin reuses Coding Plugin infrastructure without duplication."""

import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import FileArtifact, VerificationStatus
from xeren.plugins.coding.tools.execution import SubprocessSandboxExecutor
from xeren.plugins.coding.tools.syntax import SyntaxCheckTool
from xeren.plugins.website.plugin import WebsitePlugin
from xeren.plugins.website.registry import WebsiteToolRegistry


def test_registry_integrates_coding_plugin():
    """Verify WebsiteToolRegistry embeds CodingPlugin without duplicating engine."""
    coding_plugin = CodingPlugin()
    registry = WebsiteToolRegistry(coding_plugin=coding_plugin)

    assert registry.coding_plugin is coding_plugin
    # Check validator reuses coding plugin's syntax tool
    assert isinstance(registry.validator_tool.syntax_tool, SyntaxCheckTool)
    # Check generator reuses coding plugin's generation tool
    assert registry.generator_tool.coding_plugin is coding_plugin


def test_website_syntax_delegation_to_coding_syntax_tool():
    """Verify WebsiteValidatorTool delegates bracket and syntax checks to CodingPlugin's SyntaxCheckTool."""
    syntax_tool = SyntaxCheckTool()
    coding_plugin = CodingPlugin()
    coding_plugin.registry.syntax_tool = syntax_tool

    website_plugin = WebsitePlugin(coding_plugin=coding_plugin)
    assert website_plugin.registry.validator_tool.syntax_tool is syntax_tool

    # Verify syntax check error detection using Coding Plugin's syntax engine
    broken_file = FileArtifact(
        file_path="script.js",
        content="function test( { return 42; }",
        language="javascript",
    )
    res = website_plugin.validate_website([
        FileArtifact(file_path="index.html", content="<html><head></head><body></body></html>", language="html"),
        broken_file,
    ])
    assert res.validation is not None
    assert res.validation.js_ok is False
    assert any("delimiter" in d.message.lower() or "syntax" in d.message.lower() for d in res.diagnostics)


def test_website_verification_reuses_coding_test_runner():
    """Verify WebsitePlugin.verify_website can run test suites through CodingPlugin."""
    coding_plugin = CodingPlugin()
    website_plugin = WebsitePlugin(coding_plugin=coding_plugin)

    files = [
        FileArtifact(file_path="index.html", content="<html><head></head><body></body></html>", language="html"),
        FileArtifact(file_path="styles.css", content="body {}", language="css"),
        FileArtifact(file_path="script.js", content="console.log(1);", language="javascript"),
    ]

    # Run verification without inline tests
    clean_verif = website_plugin.verify_website(files)
    assert clean_verif.success is True
    assert clean_verif.verification_status == VerificationStatus.PASSED


def test_set_llm_propagates_to_coding_plugin():
    """Verify updating LLM in WebsitePlugin propagates to embedded CodingPlugin."""
    website_plugin = WebsitePlugin()
    new_llm = MockLLM()

    website_plugin.set_llm(new_llm)
    assert website_plugin.registry.llm is new_llm
    assert website_plugin.registry.coding_plugin.registry.llm is new_llm


def test_sandbox_security_boundary_shared():
    """Verify sandbox boundaries in CodingPlugin are used by Website preview/execution."""
    website_plugin = WebsitePlugin()
    assert isinstance(website_plugin.registry.coding_plugin.registry.executor, SubprocessSandboxExecutor)
