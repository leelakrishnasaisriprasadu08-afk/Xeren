"""Tool registry coordinating reader, writer, manager, search, and security tools for File Plugin."""

from pathlib import Path
from typing import Optional, Sequence, Union

from xeren.plugins.file.tools.manager import FileManagerTool
from xeren.plugins.file.tools.reader import FileReaderTool
from xeren.plugins.file.tools.search import FileSearchTool
from xeren.plugins.file.tools.security import FileSecurityTool
from xeren.plugins.file.tools.writer import FileWriterTool


class FileToolRegistry:
    """Aggregates and configures all modular file tools under unified security parameters."""

    def __init__(
        self,
        workspace_dir: Optional[Union[str, Path]] = None,
        allowed_roots: Optional[Sequence[Union[str, Path]]] = None,
        max_file_size_bytes: int = FileSecurityTool.DEFAULT_MAX_FILE_SIZE,
        redaction_enabled: bool = True,
        security_tool: Optional[FileSecurityTool] = None,
        reader_tool: Optional[FileReaderTool] = None,
        writer_tool: Optional[FileWriterTool] = None,
        manager_tool: Optional[FileManagerTool] = None,
        search_tool: Optional[FileSearchTool] = None,
    ) -> None:
        self.security_tool = security_tool or FileSecurityTool(
            workspace_dir=workspace_dir,
            allowed_roots=allowed_roots,
            max_file_size_bytes=max_file_size_bytes,
            redaction_enabled=redaction_enabled,
        )
        self.reader_tool = reader_tool or FileReaderTool(security_tool=self.security_tool)
        self.writer_tool = writer_tool or FileWriterTool(security_tool=self.security_tool)
        self.manager_tool = manager_tool or FileManagerTool(security_tool=self.security_tool)
        self.search_tool = search_tool or FileSearchTool(security_tool=self.security_tool)

    @property
    def workspace_dir(self) -> Path:
        """Active primary workspace root directory."""
        return self.security_tool.workspace_dir

    def set_workspace_dir(self, workspace_dir: Union[str, Path]) -> None:
        """Update active workspace directory across all tools."""
        self.security_tool.set_workspace_dir(workspace_dir)

    def set_max_file_size_bytes(self, max_bytes: int) -> None:
        """Update maximum file size limit."""
        self.security_tool.max_file_size_bytes = max_bytes

    def set_redaction_enabled(self, enabled: bool) -> None:
        """Toggle best-effort secret redaction."""
        self.security_tool.redaction_enabled = enabled


__all__ = ["FileToolRegistry"]
