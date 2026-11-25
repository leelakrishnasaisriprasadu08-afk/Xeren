"""Pydantic models and schemas for Model Context Protocol (MCP) server integration and cross-app workflows."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MCPTransportType(str, Enum):
    """Supported transports for connecting external MCP servers and apps."""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class MCPToolParameter(BaseModel):
    """Parameter definition for an MCP tool."""
    type: str = "string"
    description: Optional[str] = None
    default: Optional[Any] = None
    required: bool = False


class MCPTool(BaseModel):
    """Exposed tool available from an external connected MCP server."""
    name: str
    description: str
    server_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = "general"


class MCPResource(BaseModel):
    """Resource exposed by an external connected MCP server."""
    uri: str
    name: str
    mime_type: Optional[str] = "application/json"
    description: Optional[str] = None
    server_id: str


class MCPServerConfig(BaseModel):
    """Configuration for an external connected MCP application or server."""
    id: str
    name: str
    description: str
    transport: MCPTransportType = MCPTransportType.STDIO
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None
    enabled: bool = True
    status: str = "connected"  # connected, connecting, offline, error
    icon: Optional[str] = None
    category: str = "custom"  # filesystem, developer, database, web, productivity, custom
    tools: List[MCPTool] = Field(default_factory=list)
    resources: List[MCPResource] = Field(default_factory=list)


class CrossAppPipelineStep(BaseModel):
    """A single step in a multi-app collaborative workflow."""
    step_id: str
    server_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    pass_output_to_next: bool = True


class CrossAppPipeline(BaseModel):
    """Cross-app interoperability workflow where tools from multiple apps collaborate."""
    pipeline_id: str
    name: str
    description: str
    steps: List[CrossAppPipelineStep] = Field(default_factory=list)


class PipelineExecutionResult(BaseModel):
    """Result of running a cross-app interoperability workflow."""
    pipeline_id: str
    success: bool
    step_results: List[Dict[str, Any]] = Field(default_factory=list)
    final_output: Any = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None
