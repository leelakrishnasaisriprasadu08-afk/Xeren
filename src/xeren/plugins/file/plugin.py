"""File Plugin implementation adhering strictly to the Xeren BasePlugin contract."""

import asyncio
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.file.manifest import FILE_PLUGIN_MANIFEST
from xeren.plugins.file.registry import FileToolRegistry
from xeren.plugins.file.schemas import (
    FileInput,
    FileItemMetadata,
    FileOperation,
    FileResult,
    SearchResultItem,
)
from xeren.plugins.file.workflow import FileWorkflow

logger = logging.getLogger("xeren.plugins.file.plugin")


class FilePlugin(BasePlugin):
    """Production-grade filesystem plugin providing strictly verified, sandboxed file operations."""

    def __init__(
        self,
        workspace_dir: Optional[Union[str, Path]] = None,
        registry: Optional[FileToolRegistry] = None,
        workflow: Optional[FileWorkflow] = None,
    ) -> None:
        self.registry = registry or FileToolRegistry(workspace_dir=workspace_dir)
        self.workflow = workflow or FileWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return FILE_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return FileInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return FileResult

    @property
    def workspace_dir(self) -> Path:
        """Active primary workspace root directory."""
        return self.registry.workspace_dir

    def set_workspace_dir(self, workspace_dir: Union[str, Path]) -> None:
        """Update active workspace boundary directory."""
        self.registry.set_workspace_dir(workspace_dir)

    # -------------------------------------------------------------------------
    # BasePlugin Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute a filesystem operation."""
        start_time = time.perf_counter()
        try:
            validated_input: FileInput = self.validate_input(input_data)  # type: ignore
            result: FileResult = self.workflow.run(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "path": result.path,
                    "dry_run": result.dry_run,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("FilePlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"FilePlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute a filesystem operation."""
        start_time = time.perf_counter()
        try:
            validated_input: FileInput = self.validate_input(input_data)  # type: ignore
            result: FileResult = await self.workflow.arun(validated_input)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "path": result.path,
                    "dry_run": result.dry_run,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("FilePlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"FilePlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def read(
        self,
        path: str,
        encoding: str = "utf-8",
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        redaction_enabled: bool = True,
        max_size_bytes: Optional[int] = None,
        **kwargs: Any,
    ) -> FileResult:
        """Read a file within the workspace boundary."""
        inp = FileInput(
            operation=FileOperation.READ,
            path=path,
            encoding=encoding,
            line_start=line_start,
            line_end=line_end,
            redaction_enabled=redaction_enabled,
            max_size_bytes=max_size_bytes,
            metadata=kwargs,
        )
        return self.workflow.execute_read(inp)

    def write(
        self,
        path: str,
        content: str = "",
        encoding: str = "utf-8",
        overwrite: bool = True,
        create_parents: bool = True,
        atomic: bool = True,
        dry_run: bool = False,
        max_size_bytes: Optional[int] = None,
        **kwargs: Any,
    ) -> FileResult:
        """Write content to a file with atomic replacement."""
        inp = FileInput(
            operation=FileOperation.WRITE,
            path=path,
            content=content,
            encoding=encoding,
            overwrite=overwrite,
            create_parents=create_parents,
            atomic=atomic,
            dry_run=dry_run,
            max_size_bytes=max_size_bytes,
            metadata=kwargs,
        )
        return self.workflow.execute_write(inp)

    def create(
        self,
        path: str,
        content: str = "",
        encoding: str = "utf-8",
        overwrite: bool = False,
        create_parents: bool = True,
        atomic: bool = True,
        dry_run: bool = False,
        max_size_bytes: Optional[int] = None,
        **kwargs: Any,
    ) -> FileResult:
        """Create a new file. Fails if file exists and overwrite=False."""
        inp = FileInput(
            operation=FileOperation.CREATE,
            path=path,
            content=content,
            encoding=encoding,
            overwrite=overwrite,
            create_parents=create_parents,
            atomic=atomic,
            dry_run=dry_run,
            max_size_bytes=max_size_bytes,
            metadata=kwargs,
        )
        return self.workflow.execute_create(inp)

    def modify(
        self,
        path: str,
        target_content: Optional[str] = None,
        replacement: Optional[str] = None,
        content: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        encoding: str = "utf-8",
        atomic: bool = True,
        dry_run: bool = False,
        max_size_bytes: Optional[int] = None,
        **kwargs: Any,
    ) -> FileResult:
        """Modify an existing file."""
        inp = FileInput(
            operation=FileOperation.MODIFY,
            path=path,
            target_content=target_content,
            replacement=replacement,
            content=content,
            line_start=line_start,
            line_end=line_end,
            encoding=encoding,
            atomic=atomic,
            dry_run=dry_run,
            max_size_bytes=max_size_bytes,
            metadata=kwargs,
        )
        return self.workflow.execute_modify(inp)

    def delete(
        self,
        path: str,
        recursive: bool = False,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> FileResult:
        """Safely delete a file or directory. Cannot delete workspace root."""
        inp = FileInput(
            operation=FileOperation.DELETE,
            path=path,
            recursive=recursive,
            dry_run=dry_run,
            metadata=kwargs,
        )
        return self.workflow.execute_delete(inp)

    def list(
        self,
        path: Optional[str] = None,
        pattern: Optional[str] = None,
        recursive: bool = True,
        include_hidden: bool = False,
        max_results: int = 100,
        **kwargs: Any,
    ) -> List[FileItemMetadata]:
        """List files in directory returning structured metadata."""
        inp = FileInput(
            operation=FileOperation.LIST,
            path=path,
            pattern=pattern,
            recursive=recursive,
            include_hidden=include_hidden,
            max_results=max_results,
            metadata=kwargs,
        )
        res = self.workflow.execute_list(inp)
        if not res.success:
            raise PluginExecutionError(f"List failed: {res.error}", plugin_name=self.name)
        return res.items

    def search(
        self,
        pattern: Optional[str] = None,
        search_content: Optional[str] = None,
        is_regex: bool = False,
        case_sensitive: bool = True,
        path: Optional[str] = None,
        recursive: bool = True,
        include_hidden: bool = False,
        max_results: int = 100,
        **kwargs: Any,
    ) -> List[SearchResultItem]:
        """Search workspace files by filename glob and/or line content."""
        inp = FileInput(
            operation=FileOperation.SEARCH,
            path=path,
            pattern=pattern,
            search_content=search_content,
            is_regex=is_regex,
            case_sensitive=case_sensitive,
            recursive=recursive,
            include_hidden=include_hidden,
            max_results=max_results,
            metadata=kwargs,
        )
        res = self.workflow.execute_search(inp)
        if not res.success:
            raise PluginExecutionError(f"Search failed: {res.error}", plugin_name=self.name)
        return res.search_results

    def move(
        self,
        source_path: str,
        destination_path: str,
        overwrite: bool = False,
        create_parents: bool = True,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> FileResult:
        """Move or rename within workspace."""
        inp = FileInput(
            operation=FileOperation.MOVE,
            path=source_path,
            destination_path=destination_path,
            overwrite=overwrite,
            create_parents=create_parents,
            dry_run=dry_run,
            metadata=kwargs,
        )
        return self.workflow.execute_move(inp)

    def copy(
        self,
        source_path: str,
        destination_path: str,
        overwrite: bool = False,
        create_parents: bool = True,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> FileResult:
        """Copy within workspace."""
        inp = FileInput(
            operation=FileOperation.COPY,
            path=source_path,
            destination_path=destination_path,
            overwrite=overwrite,
            create_parents=create_parents,
            dry_run=dry_run,
            metadata=kwargs,
        )
        return self.workflow.execute_copy(inp)

    def metadata(self, path: str, **kwargs: Any) -> FileItemMetadata:
        """Inspect file or directory metadata."""
        inp = FileInput(
            operation=FileOperation.METADATA,
            path=path,
            metadata=kwargs,
        )
        res = self.workflow.execute_metadata(inp)
        if not res.success or res.metadata is None:
            raise PluginExecutionError(f"Metadata failed: {res.error}", plugin_name=self.name)
        return res.metadata

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Check operational readiness of the File Plugin."""
        start_time = time.perf_counter()
        if not self._initialized:
            return HealthCheckResult(
                status=PluginHealthStatus.UNHEALTHY,
                details={"initialized": False, "tools_ready": False},
                latency_ms=0.0,
                error="FilePlugin is not initialized",
            )

        workspace_exists = self.workspace_dir.exists() and self.workspace_dir.is_dir()
        details = {
            "initialized": True,
            "workspace_dir": str(self.workspace_dir),
            "workspace_exists": workspace_exists,
            "max_file_size_bytes": self.registry.security_tool.max_file_size_bytes,
            "redaction_enabled": self.registry.security_tool.redaction_enabled,
            "registered_tools_count": 5,
            "tools_ready": True,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return HealthCheckResult(
            status=PluginHealthStatus.HEALTHY if workspace_exists else PluginHealthStatus.DEGRADED,
            details=details,
            latency_ms=latency_ms,
            error=None if workspace_exists else "Workspace directory does not exist or is not a directory",
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational readiness."""
        return await asyncio.to_thread(self.health_check)

    def health(self) -> HealthCheckResult:
        """Alias conforming to standard plugin contract."""
        return self.health_check()

    def initialize(self) -> None:
        """Initialize plugin state."""
        self._initialized = True

    def shutdown(self) -> None:
        """Release plugin resources."""
        self._initialized = False


__all__ = ["FilePlugin"]
