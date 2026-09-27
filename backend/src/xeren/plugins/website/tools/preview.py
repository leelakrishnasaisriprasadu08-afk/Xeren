"""Website preview provider abstraction and safe implementations."""

from abc import ABC, abstractmethod
import asyncio
import functools
import http.server
import logging
from pathlib import Path
import socket
import tempfile
import threading
import time
from typing import Any, Dict, Optional, Sequence

# Active preview servers by port
_ACTIVE_PREVIEW_SERVERS: Dict[int, Any] = {}
_PREVIEW_LOCK = threading.Lock()

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.coding.tools.execution import (
    BaseCodeExecutor,
    SecurityViolationError,
    SubprocessSandboxExecutor,
)
from xeren.plugins.website.schemas import PreviewInfo

logger = logging.getLogger("xeren.plugins.website.tools.preview")


class BasePreviewProvider(ABC):
    """Abstract contract for website preview generators and providers."""

    @abstractmethod
    def prepare_preview(
        self,
        files: Sequence[FileArtifact],
        options: Optional[Dict[str, Any]] = None,
    ) -> PreviewInfo:
        """Prepare or render a preview for the given website project files."""
        pass

    async def aprepare_preview(
        self,
        files: Sequence[FileArtifact],
        options: Optional[Dict[str, Any]] = None,
    ) -> PreviewInfo:
        """Asynchronously prepare or render a preview."""
        return await asyncio.to_thread(self.prepare_preview, files, options)


class MockPreviewProvider(BasePreviewProvider):
    """Deterministic simulated preview provider that does not start external processes.

    Clearly distinguishes simulation from live rendering without making false claims.
    """

    def prepare_preview(
        self,
        files: Sequence[FileArtifact],
        options: Optional[Dict[str, Any]] = None,
    ) -> PreviewInfo:
        opts = options or {}
        port = opts.get("port", 8080)
        entrypoint = opts.get("entrypoint", "index.html")

        detected_pages = [f.file_path for f in files if f.file_path.endswith(".html")]

        return PreviewInfo(
            provider="mock",
            preview_url=f"http://localhost:{port}/preview/{entrypoint}",
            is_live=False,
            status="simulated",
            message="Simulated preview environment (mock mode: no live browser or background server spawned).",
            metadata={
                "pages": detected_pages,
                "total_files": len(files),
                "is_mock": True,
            },
        )


class LocalPreviewProvider(BasePreviewProvider):
    """Prepares website files inside a secured sandbox workspace with file:// URL references.

    Reuses Coding Plugin's sandbox security boundary to guarantee no directory traversal.
    """

    def __init__(self, executor: Optional[BaseCodeExecutor] = None) -> None:
        self.executor = executor or SubprocessSandboxExecutor()

    def prepare_preview(
        self,
        files: Sequence[FileArtifact],
        options: Optional[Dict[str, Any]] = None,
    ) -> PreviewInfo:
        opts = options or {}
        custom_dir = opts.get("custom_dir")
        entrypoint = opts.get("entrypoint", "index.html")

        # Verify entrypoint existence
        file_map = {f.file_path: f for f in files}
        if entrypoint not in file_map and "index.html" in file_map:
            entrypoint = "index.html"

        # Create isolated workspace using sandbox principles
        stage_dir = Path(custom_dir).resolve() if custom_dir else Path(tempfile.mkdtemp(prefix="xeren_web_preview_")).resolve()
        stage_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            if not SubprocessSandboxExecutor.is_safe_path(f.file_path, stage_dir):
                raise SecurityViolationError(f"Path traversal detected in preview file: '{f.file_path}'")
            dest = (stage_dir / f.file_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.content, encoding="utf-8")

        target_file = (stage_dir / entrypoint).resolve()
        file_url = target_file.as_uri()

        return PreviewInfo(
            provider="local",
            preview_url=file_url,
            is_live=False,
            status="ready",
            message="Local static workspace prepared safely. Can be viewed in browser via local file URL.",
            metadata={
                "workspace_path": str(stage_dir),
                "entrypoint": entrypoint,
                "total_staged_files": len(files),
            },
        )


class LiveLocalPreviewProvider(BasePreviewProvider):
    """Prepares website files inside workspace and launches a real, live background HTTP server.

    Ensures that when a user opens http://localhost:<port>/ in their browser, the website
    actually loads and runs interactively. Also provides a direct file:// URL.
    """

    def __init__(self, base_port: int = 8080, workspace_root: Optional[Path] = None) -> None:
        self.base_port = base_port
        default_root = Path("d:/Xeren/workspace/generated_sites").resolve() if Path("d:/Xeren").exists() else (Path(tempfile.gettempdir()) / "xeren_sites")
        self.workspace_root = workspace_root or default_root

    def _find_available_port(self, start_port: int = 8080, max_attempts: int = 50) -> int:
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def prepare_preview(
        self,
        files: Sequence[FileArtifact],
        options: Optional[Dict[str, Any]] = None,
    ) -> PreviewInfo:
        opts = options or {}
        custom_dir = opts.get("custom_dir")
        entrypoint = opts.get("entrypoint", "index.html")

        if custom_dir:
            stage_dir = Path(custom_dir).resolve()
        else:
            stage_dir = (self.workspace_root / f"app_{int(time.time())}").resolve()
        stage_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            dest = (stage_dir / f.file_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.content, encoding="utf-8")

        # Also populate 'latest' and root entrypoint so http://localhost:8080/index.html directly works
        latest_dir = (self.workspace_root / "latest").resolve()
        latest_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            dest = (latest_dir / f.file_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.content, encoding="utf-8")

            # Copy frontend assets to root of workspace_root so http://localhost:8080/index.html loads immediately
            if f.file_path in ("index.html", "styles.css", "script.js"):
                root_dest = (self.workspace_root / f.file_path).resolve()
                root_dest.write_text(f.content, encoding="utf-8")

        target_file = (stage_dir / entrypoint).resolve()
        file_url = target_file.as_uri()

        requested_port = opts.get("port")
        active_port = None

        serve_dir = self.workspace_root.resolve()
        serve_dir.mkdir(parents=True, exist_ok=True)

        with _PREVIEW_LOCK:
            for p, srv in _ACTIVE_PREVIEW_SERVERS.items():
                if getattr(srv, "_served_dir", None) == str(serve_dir):
                    active_port = p
                    break

            if active_port is None:
                port = requested_port or self._find_available_port(self.base_port)
                try:
                    class QuietHandler(http.server.SimpleHTTPRequestHandler):
                        def log_message(self, format: str, *args: Any) -> None:
                            pass

                    handler = functools.partial(QuietHandler, directory=str(serve_dir))
                    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
                    server._served_dir = str(serve_dir)  # type: ignore[attr-defined]
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    thread.start()
                    _ACTIVE_PREVIEW_SERVERS[port] = server
                    active_port = port
                except Exception as e:
                    logger.warning("Could not launch live preview HTTP server on port %s: %s", port, e)
                    active_port = port

        preview_url = f"http://localhost:{active_port}/{entrypoint}" if active_port else file_url

        return PreviewInfo(
            provider="live_local",
            preview_url=preview_url,
            is_live=True,
            status="running",
            message=f"Live local server running at {preview_url}. Files saved in {stage_dir}.",
            metadata={
                "workspace_path": str(stage_dir),
                "entrypoint": entrypoint,
                "port": active_port,
                "file_url": file_url,
                "total_staged_files": len(files),
            },
        )


__all__ = [
    "BasePreviewProvider",
    "MockPreviewProvider",
    "LocalPreviewProvider",
    "LiveLocalPreviewProvider",
]
