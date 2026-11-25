"""Pre-configured presets for popular apps and cross-app collaborative workflows."""

from __future__ import annotations

from typing import List
from xeren.mcp.schemas import (
    MCPServerConfig,
    MCPTool,
    MCPResource,
    MCPTransportType,
    CrossAppPipeline,
    CrossAppPipelineStep,
)


def get_default_mcp_presets() -> List[MCPServerConfig]:
    """Return pre-configured popular apps with realistic tool signatures."""
    return [
        MCPServerConfig(
            id="os_connector",
            name="OS & Device Connector",
            description="Direct Python-native device access: read/write local files, launch apps, list running processes. Permission-gated by the orchestrator.",
            transport=MCPTransportType.STDIO,
            command="python",
            args=["-m", "xeren.mcp.os_connector"],
            enabled=True,
            status="connected",
            icon="🖥️",
            category="system",
            tools=[
                MCPTool(
                    name="read_file",
                    description="Read a local file by absolute path (user must grant permission).",
                    server_id="os_connector",
                    parameters={"path": {"type": "string", "description": "Absolute path to the file"}},
                    category="filesystem",
                ),
                MCPTool(
                    name="write_file",
                    description="Write content to a local file (user must grant permission).",
                    server_id="os_connector",
                    parameters={
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    category="filesystem",
                ),
                MCPTool(
                    name="list_directory",
                    description="List contents of a local directory.",
                    server_id="os_connector",
                    parameters={"path": {"type": "string"}},
                    category="filesystem",
                ),
                MCPTool(
                    name="launch_app",
                    description="Launch a local application by name/path (user must grant permission).",
                    server_id="os_connector",
                    parameters={
                        "app": {"type": "string"},
                        "args": {"type": "array", "items": {"type": "string"}},
                    },
                    category="system",
                ),
                MCPTool(
                    name="list_running_apps",
                    description="List currently running applications/processes on this device.",
                    server_id="os_connector",
                    parameters={},
                    category="system",
                ),
            ],
        ),
        MCPServerConfig(
            id="filesystem",

            name="Local Filesystem",
            description="Secure local workspace file and directory management across project folders.",
            transport=MCPTransportType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "./workspace"],
            enabled=True,
            status="connected",
            icon="📁",
            category="filesystem",
            tools=[
                MCPTool(
                    name="read_file",
                    description="Read complete contents of a file at path.",
                    server_id="filesystem",
                    parameters={"path": {"type": "string", "description": "Relative or absolute file path"}},
                    category="filesystem",
                ),
                MCPTool(
                    name="write_file",
                    description="Write or overwrite content into a target file path.",
                    server_id="filesystem",
                    parameters={
                        "path": {"type": "string", "description": "Destination file path"},
                        "content": {"type": "string", "description": "Text content to write"},
                    },
                    category="filesystem",
                ),
                MCPTool(
                    name="list_directory",
                    description="List files and subdirectories with sizes and timestamps.",
                    server_id="filesystem",
                    parameters={"path": {"type": "string", "description": "Directory path"}},
                    category="filesystem",
                ),
            ],
            resources=[
                MCPResource(
                    uri="file:///workspace",
                    name="Default Workspace Root",
                    mime_type="application/directory",
                    server_id="filesystem",
                )
            ],
        ),
        MCPServerConfig(
            id="github",
            name="GitHub Assistant",
            description="Inspect repositories, manage issues, and generate automated pull requests.",
            transport=MCPTransportType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
            enabled=True,
            status="connected",
            icon="🐙",
            category="developer",
            tools=[
                MCPTool(
                    name="list_issues",
                    description="Fetch recent open issues and bugs from a GitHub repo.",
                    server_id="github",
                    parameters={
                        "repo": {"type": "string", "description": "owner/repo name"},
                        "state": {"type": "string", "description": "open or closed", "default": "open"},
                    },
                    category="developer",
                ),
                MCPTool(
                    name="create_issue_comment",
                    description="Add an automated comment or PR response to a GitHub issue.",
                    server_id="github",
                    parameters={
                        "repo": {"type": "string", "description": "owner/repo name"},
                        "issue_number": {"type": "integer", "description": "Issue number"},
                        "comment": {"type": "string", "description": "Markdown comment text"},
                    },
                    category="developer",
                ),
                MCPTool(
                    name="create_pull_request",
                    description="Open a new pull request with title, branch, and changelog.",
                    server_id="github",
                    parameters={
                        "repo": {"type": "string", "description": "owner/repo name"},
                        "title": {"type": "string", "description": "PR title"},
                        "branch": {"type": "string", "description": "Head branch"},
                    },
                    category="developer",
                ),
            ],
        ),
        MCPServerConfig(
            id="sqlite",
            name="SQLite Database",
            description="Query, inspect schemas, and mutate local SQLite relational tables.",
            transport=MCPTransportType.STDIO,
            command="python",
            args=["-m", "mcp_server_sqlite", "--db-path", "./data/xeren.db"],
            enabled=True,
            status="connected",
            icon="🗄️",
            category="database",
            tools=[
                MCPTool(
                    name="execute_query",
                    description="Run an analytical or transactional SQL query.",
                    server_id="sqlite",
                    parameters={"query": {"type": "string", "description": "SQL statement to run"}},
                    category="database",
                ),
                MCPTool(
                    name="list_tables",
                    description="List all tables, column types, and row count metrics.",
                    server_id="sqlite",
                    parameters={},
                    category="database",
                ),
            ],
        ),
        MCPServerConfig(
            id="puppeteer",
            name="Puppeteer Web Automation",
            description="Automated headless browser navigation, DOM extraction, and visual screenshots.",
            transport=MCPTransportType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-puppeteer"],
            enabled=False,
            status="offline",
            icon="🌐",
            category="web",
            tools=[
                MCPTool(
                    name="navigate",
                    description="Navigate browser to target URL and wait for DOM load.",
                    server_id="puppeteer",
                    parameters={"url": {"type": "string", "description": "Target webpage URL"}},
                    category="web",
                ),
                MCPTool(
                    name="extract_text",
                    description="Extract readable text and heading structure from active page.",
                    server_id="puppeteer",
                    parameters={"selector": {"type": "string", "description": "CSS selector to target"}},
                    category="web",
                ),
            ],
        ),
        MCPServerConfig(
            id="slack",
            name="Slack Workspace",
            description="Send automated team notifications, read messages, and post alert summaries.",
            transport=MCPTransportType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-slack"],
            env={"SLACK_BOT_TOKEN": ""},
            enabled=True,
            status="connected",
            icon="💬",
            category="productivity",
            tools=[
                MCPTool(
                    name="send_message",
                    description="Post formatted message to a Slack channel or thread.",
                    server_id="slack",
                    parameters={
                        "channel": {"type": "string", "description": "Channel name or ID"},
                        "text": {"type": "string", "description": "Message body"},
                    },
                    category="productivity",
                ),
                MCPTool(
                    name="list_channels",
                    description="List accessible public and private Slack channels.",
                    server_id="slack",
                    parameters={},
                    category="productivity",
                ),
            ],
        ),
        MCPServerConfig(
            id="docker",
            name="Docker Container Runtime",
            description="Inspect Docker containers, tail build logs, and manage isolated sandbox runtimes.",
            transport=MCPTransportType.STDIO,
            command="python",
            args=["-m", "mcp_docker"],
            enabled=False,
            status="offline",
            icon="🐳",
            category="developer",
            tools=[
                MCPTool(
                    name="list_containers",
                    description="List running Docker containers and health states.",
                    server_id="docker",
                    parameters={"all": {"type": "boolean", "default": False}},
                    category="developer",
                ),
                MCPTool(
                    name="run_container",
                    description="Launch an isolated container from an image with environment.",
                    server_id="docker",
                    parameters={
                        "image": {"type": "string", "description": "Docker image name"},
                        "command": {"type": "string", "description": "Startup command"},
                    },
                    category="developer",
                ),
            ],
        ),
        MCPServerConfig(
            id="brave-search",
            name="Brave Web Search",
            description="High-privacy web index queries and real-time news retrieval.",
            transport=MCPTransportType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={"BRAVE_API_KEY": ""},
            enabled=True,
            status="connected",
            icon="🔍",
            category="web",
            tools=[
                MCPTool(
                    name="brave_web_search",
                    description="Search the live web for authoritative sources and documents.",
                    server_id="brave-search",
                    parameters={"query": {"type": "string", "description": "Search keywords"}},
                    category="web",
                )
            ],
        ),
    ]


def get_default_cross_app_pipelines() -> List[CrossAppPipeline]:
    """Pre-built multi-app interoperability workflows showing how apps work with each other."""
    return [
        CrossAppPipeline(
            pipeline_id="github-to-code-to-slack",
            name="GitHub Bug Fix ➔ Local Code Patch ➔ Audit DB ➔ Slack Alert",
            description="Fetches an open issue from GitHub, writes a local solution patch to filesystem, logs execution to SQLite, and alerts team on Slack.",
            steps=[
                CrossAppPipelineStep(
                    step_id="step-1",
                    server_id="github",
                    tool_name="list_issues",
                    arguments={"repo": "xeren-org/core", "state": "open"},
                    description="1. Fetch latest open bug report from GitHub",
                    pass_output_to_next=True,
                ),
                CrossAppPipelineStep(
                    step_id="step-2",
                    server_id="filesystem",
                    tool_name="write_file",
                    arguments={"path": "patches/issue_patch.py", "content": "# Automated patch generated by Xeren\ndef resolve_bug(): return True"},
                    description="2. Generate and write code patch to Local Filesystem",
                    pass_output_to_next=True,
                ),
                CrossAppPipelineStep(
                    step_id="step-3",
                    server_id="sqlite",
                    tool_name="execute_query",
                    arguments={"query": "INSERT INTO task_history (app, action, status) VALUES ('github', 'patch_generated', 'success')"},
                    description="3. Record execution audit in SQLite Database",
                    pass_output_to_next=True,
                ),
                CrossAppPipelineStep(
                    step_id="step-4",
                    server_id="slack",
                    tool_name="send_message",
                    arguments={"channel": "#engineering", "text": "✅ Xeren resolved GitHub Issue: Patch written and recorded to database."},
                    description="4. Broadcast confirmation to team on Slack",
                    pass_output_to_next=False,
                ),
            ],
        ),
        CrossAppPipeline(
            pipeline_id="web-research-to-vault-to-filesystem",
            name="Brave Web Research ➔ Synthesis ➔ SQLite Ingestion ➔ Project File",
            description="Queries Brave Search for benchmarks, inserts findings into SQLite database, and creates a local summary markdown report.",
            steps=[
                CrossAppPipelineStep(
                    step_id="step-1",
                    server_id="brave-search",
                    tool_name="brave_web_search",
                    arguments={"query": "agentic AI MCP architecture 2026"},
                    description="1. Search web for latest agentic benchmarks via Brave Search",
                    pass_output_to_next=True,
                ),
                CrossAppPipelineStep(
                    step_id="step-2",
                    server_id="sqlite",
                    tool_name="execute_query",
                    arguments={"query": "INSERT INTO research_cache (topic, source) VALUES ('agentic AI', 'brave_search')"},
                    description="2. Store search telemetry in SQLite",
                    pass_output_to_next=True,
                ),
                CrossAppPipelineStep(
                    step_id="step-3",
                    server_id="filesystem",
                    tool_name="write_file",
                    arguments={"path": "docs/RESEARCH_SUMMARY.md", "content": "# Agentic AI & MCP Report\nSynthesized across multi-app pipeline."},
                    description="3. Compile comprehensive report in Filesystem",
                    pass_output_to_next=False,
                ),
            ],
        ),
    ]
