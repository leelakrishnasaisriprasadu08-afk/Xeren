"""Website preview provider abstraction and safe implementations."""

from abc import ABC, abstractmethod
import asyncio
import logging
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional, Sequence

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


__all__ = [
    "BasePreviewProvider",
    "MockPreviewProvider",
    "LocalPreviewProvider",
]
