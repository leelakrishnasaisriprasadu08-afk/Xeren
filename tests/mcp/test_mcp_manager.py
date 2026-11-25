"""Tests for Xeren MCP Manager and Cross-App Interoperability Subsystem."""

import pytest
from xeren.mcp.schemas import (
    MCPServerConfig,
    MCPTool,
    MCPTransportType,
    CrossAppPipeline,
    CrossAppPipelineStep,
)
from xeren.mcp.manager import MCPManager
from xeren.mcp.presets import get_default_mcp_presets, get_default_cross_app_pipelines


def test_mcp_manager_initialization_with_defaults():
    mgr = MCPManager(load_defaults=True)
    servers = mgr.list_servers()
    assert len(servers) >= 6
    server_ids = [s.id for s in servers]
    assert "filesystem" in server_ids
    assert "github" in server_ids
    assert "sqlite" in server_ids
    assert "slack" in server_ids


def test_mcp_manager_server_toggle_and_remove():
    mgr = MCPManager(load_defaults=True)
    server = mgr.toggle_server("github", enabled=False)
    assert server.enabled is False
    assert server.status == "offline"

    server = mgr.toggle_server("github", enabled=True)
    assert server.enabled is True
    assert server.status == "connected"

    # Remove server
    removed = mgr.remove_server("github")
    assert removed is True
    assert mgr.get_server("github") is None


def test_mcp_manager_register_custom_server():
    mgr = MCPManager(load_defaults=False)
    custom_server = MCPServerConfig(
        id="custom-crm",
        name="HubSpot Custom CRM",
        description="Sync client contacts and deals via MCP.",
        transport=MCPTransportType.SSE,
        url="http://localhost:9090/sse",
        tools=[
            MCPTool(
                name="get_contact",
                description="Fetch contact by email",
                server_id="custom-crm",
                parameters={"email": {"type": "string"}},
            )
        ],
    )
    mgr.register_server(custom_server)
    assert mgr.get_server("custom-crm") is not None
    assert len(mgr.list_all_tools()) == 1


def test_mcp_manager_call_tool_dispatch():
    mgr = MCPManager(load_defaults=True)
    # 1. Filesystem write tool
    fs_res = mgr.call_tool("filesystem", "write_file", {"path": "test.txt", "content": "Hello MCP"})
    assert fs_res["success"] is True
    assert fs_res["output"]["status"] == "written"
    assert fs_res["output"]["bytes_written"] == 9

    # 2. GitHub list issues
    gh_res = mgr.call_tool("github", "list_issues", {"repo": "xeren-org/core"})
    assert gh_res["success"] is True
    assert len(gh_res["output"]) >= 1

    # 3. Calling tool on disabled server raises ValueError
    mgr.toggle_server("filesystem", enabled=False)
    with pytest.raises(ValueError, match="currently offline"):
        mgr.call_tool("filesystem", "write_file", {"path": "test.txt"})


def test_cross_app_pipeline_execution():
    """Verify that multiple connected apps work with each other in a pipeline."""
    mgr = MCPManager(load_defaults=True)
    pipelines = mgr.list_pipelines()
    assert len(pipelines) >= 1

    pipeline = pipelines[0]
    result = mgr.execute_cross_app_pipeline(pipeline)

    assert result.success is True
    assert result.pipeline_id == pipeline.pipeline_id
    assert len(result.step_results) == len(pipeline.steps)
    assert result.execution_time_ms >= 0

    # Ensure each step completed successfully
    for step in result.step_results:
        assert step["success"] is True
        assert "latency_ms" in step
        assert step["output"] is not None
