"""Model Context Protocol (MCP) and Cross-App Interoperability Subsystem for Xeren."""

from xeren.mcp.schemas import (
    MCPTransportType,
    MCPServerConfig,
    MCPTool,
    MCPResource,
    CrossAppPipelineStep,
    CrossAppPipeline,
    PipelineExecutionResult,
)
from xeren.mcp.manager import MCPManager
from xeren.mcp.presets import get_default_mcp_presets, get_default_cross_app_pipelines

__all__ = [
    "MCPTransportType",
    "MCPServerConfig",
    "MCPTool",
    "MCPResource",
    "CrossAppPipelineStep",
    "CrossAppPipeline",
    "PipelineExecutionResult",
    "MCPManager",
    "get_default_mcp_presets",
    "get_default_cross_app_pipelines",
]
