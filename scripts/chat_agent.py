"""Interactive Terminal Chat for Xeren Autonomous AI Workstation.

Provides the exact same capabilities as the Xeren Frontend UI:
- Realtime WebSocket streaming with word-by-word token delivery
- Autonomous task planning and 'proceed to the plan' staged execution
- Agent activity progress updates (researching, planning, executing)
- Rich Markdown rendering, syntax-highlighted code blocks, and formatted tables
- Connects to running FastAPI backend (port 8000) or runs in direct in-process Core mode
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, Optional

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add src to python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text
from rich.theme import Theme

# Custom sleek Xeren theme
xeren_theme = Theme({
    "xeren.brand": "bold cyan",
    "xeren.accent": "bold green",
    "xeren.dim": "dim grey70",
    "xeren.warning": "bold yellow",
    "xeren.error": "bold red",
    "xeren.progress": "cyan",
})
console = Console(theme=xeren_theme)

WS_URL = "ws://127.0.0.1:8000/api/v1/realtime"
HTTP_HEALTH_URL = "http://127.0.0.1:8000/api/health"
HTTP_CHAT_URL = "http://127.0.0.1:8000/api/chat"
HTTP_PLAN_URL = "http://127.0.0.1:8000/api/plan/active"


async def check_backend_online() -> bool:
    """Check if the Xeren FastAPI backend is online and accepting connections."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=1.0) as client:
            res = await client.get(HTTP_HEALTH_URL)
            return res.status_code == 200
    except Exception:
        return False


class WebSocketChatClient:
    """Connects to the running Xeren FastAPI server via WebSocket."""

    def __init__(self, ws_url: str = WS_URL):
        self.ws_url = ws_url
        self.session_id: Optional[str] = None

    async def stream_query(
        self,
        query: str,
        on_status: Callable[[str], None],
        on_delta: Callable[[str], None],
    ) -> str:
        """Sends a query over the realtime websocket and yields tokens."""
        import websockets
        accumulated_text = ""

        async with websockets.connect(self.ws_url) as ws:
            # 1. Receive conversation.start
            start_msg = await ws.recv()
            try:
                start_evt = json.loads(start_msg)
                self.session_id = start_evt.get("session_id")
            except Exception:
                pass

            # 2. Send user message
            await ws.send(json.dumps({
                "type": "user.text",
                "text": query,
            }))

            # 3. Stream events until response.done
            while True:
                raw_evt = await ws.recv()
                try:
                    evt = json.loads(raw_evt)
                except Exception:
                    continue

                evt_type = evt.get("type")

                if evt_type == "agent.status":
                    activity = evt.get("activityTitle", "Processing task...")
                    on_status(activity)

                elif evt_type == "response.text.delta":
                    delta = evt.get("delta", "")
                    accumulated_text += delta
                    on_delta(delta)

                elif evt_type == "response.text.complete":
                    accumulated_text = evt.get("text", accumulated_text)

                elif evt_type == "response.done":
                    break

        return accumulated_text


class StandaloneCoreClient:
    """Runs XerenCore directly in-process if backend server is not running."""

    def __init__(self):
        from xeren.core.runtime import XerenCore
        from xeren.core.session import XerenSession
        self.session = XerenSession()
        self.core = XerenCore(session=self.session, auto_register_defaults=True)

    async def stream_query(
        self,
        query: str,
        on_status: Callable[[str], None],
        on_delta: Callable[[str], None],
    ) -> str:
        accumulated_text = ""

        async def _on_progress(progress_data: Dict[str, Any]):
            activity = progress_data.get("activityTitle", "Executing task...")
            on_status(activity)

        async for chunk in self.core.astream_chat(query, on_progress=_on_progress):
            accumulated_text += chunk
            on_delta(chunk)

        return accumulated_text

    def get_staged_plan(self) -> Optional[Any]:
        return self.session.get_staged_plan()


def print_banner(is_server_mode: bool, session_id: Optional[str] = None):
    mode_str = "[bold green]● Connected to Backend (ws://127.0.0.1:8000)[/bold green]" if is_server_mode else "[bold yellow]● In-Process Autonomous Engine (Standalone Core)[/bold yellow]"
    
    body = Text()
    body.append("⚡ XEREN AUTONOMOUS WORKSTATION — TERMINAL AGENT\n", style="bold cyan")
    body.append(f"Status : {mode_str}\n")
    if session_id:
        body.append(f"Session: [dim]{session_id}[/dim]\n")
    body.append("\nCommands:\n", style="bold white")
    body.append("  • Type any question or coding task to converse in realtime\n", style="dim")
    body.append("  • Say [bold green]'proceed to the plan'[/bold green] or type [cyan]/proceed[/cyan] to execute a staged plan\n", style="dim")
    body.append("  • Type [cyan]/plan[/cyan] to view staged plan, [cyan]/clear[/cyan] to clear screen, [cyan]/exit[/cyan] to quit\n", style="dim")

    console.print(Panel(body, border_style="cyan", padding=(1, 2)))


async def main():
    # Detect backend availability
    backend_online = await check_backend_online()
    
    ws_client: Optional[WebSocketChatClient] = None
    core_client: Optional[StandaloneCoreClient] = None

    if backend_online:
        ws_client = WebSocketChatClient()
    else:
        console.print("[dim]Backend server on port 8000 not detected. Initializing in-process Xeren Core...[/dim]")
        core_client = StandaloneCoreClient()

    print_banner(is_server_mode=backend_online)

    while True:
        try:
            user_input = console.input("\n[bold green]You[/bold green] [dim]›[/dim] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Exiting Xeren chat. Goodbye![/yellow]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/exit", "/quit", "exit", "quit", "q"):
            console.print("[yellow]Session ended. Have a productive day![/yellow]")
            break

        if cmd in ("/clear", "clear", "cls"):
            os.system("cls" if os.name == "nt" else "clear")
            print_banner(is_server_mode=backend_online)
            continue

        if cmd == "/proceed":
            user_input = "proceed to the plan"

        if cmd == "/plan":
            if backend_online:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        resp = await client.get(HTTP_PLAN_URL)
                        data = resp.json()
                        if data.get("staged") and data.get("plan"):
                            console.print(Panel(JSON.dumps(data["plan"], indent=2), title="Active Staged Plan", border_style="cyan"))
                        else:
                            console.print("[dim]No active plan currently staged.[/dim]")
                except Exception as err:
                    console.print(f"[red]Error fetching active plan: {err}[/red]")
            elif core_client:
                plan = core_client.get_staged_plan()
                if plan:
                    console.print(Panel(str(plan), title="Active Staged Plan", border_style="cyan"))
                else:
                    console.print("[dim]No active plan currently staged.[/dim]")
            continue

        # Realtime Response Handling
        try:
            accumulated = ""
            with Live(
                Panel(Markdown("⚡ *Thinking & orchestrating...*"), title="[bold cyan]⚡ Xeren[/bold cyan]", border_style="cyan", padding=(1, 2)),
                console=console,
                refresh_per_second=10,
            ) as live:
                def on_status_update(act: str):
                    if not accumulated:
                        live.update(Panel(Markdown(f"⚡ *{act}...*"), title="[bold cyan]⚡ Xeren[/bold cyan]", border_style="cyan", padding=(1, 2)))

                def on_delta_update(delta: str):
                    nonlocal accumulated
                    accumulated += delta
                    live.update(Panel(Markdown(accumulated), title="[bold cyan]⚡ Xeren[/bold cyan]", border_style="cyan", padding=(1, 2)))

                if ws_client:
                    try:
                        reply = await ws_client.stream_query(
                            user_input,
                            on_status=on_status_update,
                            on_delta=on_delta_update,
                        )
                    except Exception as ws_err:
                        console.print(f"\n[yellow]WebSocket connection interrupted ({ws_err}). Switching to direct Core...[/yellow]")
                        if not core_client:
                            core_client = StandaloneCoreClient()
                        reply = await core_client.stream_query(
                            user_input,
                            on_status=on_status_update,
                            on_delta=on_delta_update,
                        )
                else:
                    reply = await core_client.stream_query(
                        user_input,
                        on_status=on_status_update,
                        on_delta=on_delta_update,
                    )

                live.update(Panel(Markdown(reply or accumulated), title="[bold cyan]⚡ Xeren[/bold cyan]", border_style="cyan", padding=(1, 2)))

        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    asyncio.run(main())
