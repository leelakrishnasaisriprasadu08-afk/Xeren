"""Workflow orchestrator dispatching file operations with latency metrics, dry-run previews, and error isolation."""

import asyncio
import logging
from pathlib import Path
import shutil
import time
from typing import Optional, Union

from xeren.plugins.file.registry import FileToolRegistry
from xeren.plugins.file.schemas import FileInput, FileOperation, FileResult

logger = logging.getLogger("xeren.plugins.file.workflow")


class FileWorkflow:
    """Orchestrates filesystem operations using registered modular file tools."""

    def __init__(self, registry: Optional[FileToolRegistry] = None) -> None:
        self.registry = registry or FileToolRegistry()

    def run(self, input_data: FileInput) -> FileResult:
        """Synchronously route and execute a file operation."""
        handler_map = {
            FileOperation.READ: self.execute_read,
            FileOperation.WRITE: self.execute_write,
            FileOperation.CREATE: self.execute_create,
            FileOperation.MODIFY: self.execute_modify,
            FileOperation.DELETE: self.execute_delete,
            FileOperation.LIST: self.execute_list,
            FileOperation.SEARCH: self.execute_search,
            FileOperation.MOVE: self.execute_move,
            FileOperation.COPY: self.execute_copy,
            FileOperation.METADATA: self.execute_metadata,
        }

        handler = handler_map.get(input_data.operation)
        if not handler:
            return FileResult(
                operation=input_data.operation,
                success=False,
                error=f"Unsupported file operation: '{input_data.operation}'",
            )

        return handler(input_data)

    async def arun(self, input_data: FileInput) -> FileResult:
        """Asynchronously route and execute a file operation."""
        return await asyncio.to_thread(self.run, input_data)

    # -------------------------------------------------------------------------
    # Handlers
    # -------------------------------------------------------------------------
    def execute_read(self, input_data: FileInput) -> FileResult:
        """Execute read operation."""
        start = time.perf_counter()
        if not input_data.path:
            return FileResult(
                operation=FileOperation.READ,
                success=False,
                error="Path is required for read operation",
            )
        try:
            res = self.registry.reader_tool.read_file(
                raw_path=input_data.path,
                encoding=input_data.encoding,
                max_size_bytes=input_data.max_size_bytes,
                line_start=input_data.line_start,
                line_end=input_data.line_end,
                redaction_enabled=input_data.redaction_enabled,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.READ,
                success=res["success"],
                path=res["path"],
                content=res["content"],
                bytes_read=res["bytes_read"],
                warning=res.get("warning"),
                redacted_secrets=res.get("redacted_secrets", False),
                stats={"latency_ms": latency, "is_binary": res.get("is_binary", False)},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File read failed for '%s': %s", input_data.path, err)
            return FileResult(
                operation=FileOperation.READ,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def _create_snapshot_if_needed(self, raw_path: Union[str, Path]) -> Optional[str]:
        """Create automatic rollback snapshot before modifying an existing file."""
        try:
            target = self.registry.security_tool.resolve_and_validate_path(raw_path, must_exist=False)
            if target.is_file():
                snapshot_dir = self.registry.workspace_dir / ".xeren" / "snapshots"
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                timestamp = int(time.time())
                sanitized_name = f"{target.name}_{timestamp}.bak"
                snapshot_path = snapshot_dir / sanitized_name
                shutil.copy2(target, snapshot_path)
                return str(snapshot_path)
        except Exception as e:
            logger.debug("Failed to create pre-modification snapshot for '%s': %s", raw_path, e)
        return None

    def execute_write(self, input_data: FileInput) -> FileResult:
        """Execute write operation with automated rollback snapshot."""
        start = time.perf_counter()
        if not input_data.path:
            return FileResult(
                operation=FileOperation.WRITE,
                success=False,
                error="Path is required for write operation",
            )
        try:
            snapshot = self._create_snapshot_if_needed(input_data.path)
            res = self.registry.writer_tool.write_file(
                raw_path=input_data.path,
                content=input_data.content or "",
                encoding=input_data.encoding,
                overwrite=input_data.overwrite,
                create_parents=input_data.create_parents,
                atomic=input_data.atomic,
                max_size_bytes=input_data.max_size_bytes,
                dry_run=input_data.dry_run,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            stats = {"latency_ms": latency, "checksum_sha256": res.get("checksum_sha256")}
            if snapshot:
                stats["snapshot"] = snapshot
            return FileResult(
                operation=FileOperation.WRITE,
                success=res["success"],
                path=res["path"],
                bytes_written=res["bytes_written"],
                dry_run=res.get("dry_run", False),
                stats=stats,
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File write failed for '%s': %s", input_data.path, err)
            return FileResult(
                operation=FileOperation.WRITE,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_create(self, input_data: FileInput) -> FileResult:
        """Execute create operation (fails if file exists and overwrite=False)."""
        start = time.perf_counter()
        if not input_data.path:
            return FileResult(
                operation=FileOperation.CREATE,
                success=False,
                error="Path is required for create operation",
            )
        try:
            res = self.registry.writer_tool.create_file(
                raw_path=input_data.path,
                content=input_data.content or "",
                encoding=input_data.encoding,
                overwrite=input_data.overwrite,
                create_parents=input_data.create_parents,
                atomic=input_data.atomic,
                max_size_bytes=input_data.max_size_bytes,
                dry_run=input_data.dry_run,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.CREATE,
                success=res["success"],
                path=res["path"],
                bytes_written=res["bytes_written"],
                dry_run=res.get("dry_run", False),
                stats={"latency_ms": latency, "checksum_sha256": res.get("checksum_sha256")},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File create failed for '%s': %s", input_data.path, err)
            return FileResult(
                operation=FileOperation.CREATE,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_modify(self, input_data: FileInput) -> FileResult:
        """Execute modify operation."""
        start = time.perf_counter()
        if not input_data.path:
            return FileResult(
                operation=FileOperation.MODIFY,
                success=False,
                error="Path is required for modify operation",
            )
        try:
            res = self.registry.writer_tool.modify_file(
                raw_path=input_data.path,
                target_content=input_data.target_content,
                replacement=input_data.replacement,
                new_full_content=input_data.content,
                line_start=input_data.line_start,
                line_end=input_data.line_end,
                encoding=input_data.encoding,
                atomic=input_data.atomic,
                max_size_bytes=input_data.max_size_bytes,
                dry_run=input_data.dry_run,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.MODIFY,
                success=res["success"],
                path=res["path"],
                bytes_written=res["bytes_written"],
                dry_run=res.get("dry_run", False),
                stats={"latency_ms": latency, "checksum_sha256": res.get("checksum_sha256")},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File modify failed for '%s': %s", input_data.path, err)
            return FileResult(
                operation=FileOperation.MODIFY,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_delete(self, input_data: FileInput) -> FileResult:
        """Execute delete operation."""
        start = time.perf_counter()
        if not input_data.path:
            return FileResult(
                operation=FileOperation.DELETE,
                success=False,
                error="Path is required for delete operation",
            )
        try:
            res = self.registry.manager_tool.delete_entity(
                raw_path=input_data.path,
                recursive=input_data.recursive,
                dry_run=input_data.dry_run,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.DELETE,
                success=res["success"],
                path=res["path"],
                dry_run=res.get("dry_run", False),
                stats={"latency_ms": latency, "is_directory": res.get("is_directory", False)},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File delete failed for '%s': %s", input_data.path, err)
            return FileResult(
                operation=FileOperation.DELETE,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_list(self, input_data: FileInput) -> FileResult:
        """Execute directory listing."""
        start = time.perf_counter()
        try:
            items = self.registry.manager_tool.list_directory(
                raw_path=input_data.path,
                pattern=input_data.pattern,
                recursive=input_data.recursive,
                include_hidden=input_data.include_hidden,
                max_results=input_data.max_results,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.LIST,
                success=True,
                path=input_data.path or ".",
                items=items,
                stats={"latency_ms": latency, "count": len(items)},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File list failed for '%s': %s", input_data.path, err)
            return FileResult(
                operation=FileOperation.LIST,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_search(self, input_data: FileInput) -> FileResult:
        """Execute file search (pattern and/or text/regex content)."""
        start = time.perf_counter()
        try:
            matches = self.registry.search_tool.search(
                raw_path=input_data.path,
                pattern=input_data.pattern,
                search_content=input_data.search_content,
                is_regex=input_data.is_regex,
                case_sensitive=input_data.case_sensitive,
                recursive=input_data.recursive,
                include_hidden=input_data.include_hidden,
                max_results=input_data.max_results,
                encoding=input_data.encoding,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.SEARCH,
                success=True,
                path=input_data.path or ".",
                search_results=matches,
                stats={"latency_ms": latency, "count": len(matches)},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File search failed: %s", err)
            return FileResult(
                operation=FileOperation.SEARCH,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_move(self, input_data: FileInput) -> FileResult:
        """Execute move or rename."""
        start = time.perf_counter()
        if not input_data.path or not input_data.destination_path:
            return FileResult(
                operation=FileOperation.MOVE,
                success=False,
                error="Both path and destination_path are required for move operation",
            )
        try:
            res = self.registry.manager_tool.move_entity(
                source_path=input_data.path,
                destination_path=input_data.destination_path,
                overwrite=input_data.overwrite,
                create_parents=input_data.create_parents,
                dry_run=input_data.dry_run,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.MOVE,
                success=res["success"],
                path=res["path"],
                destination_path=res["destination_path"],
                dry_run=res.get("dry_run", False),
                stats={"latency_ms": latency},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File move failed from '%s' to '%s': %s", input_data.path, input_data.destination_path, err)
            return FileResult(
                operation=FileOperation.MOVE,
                success=False,
                path=input_data.path,
                destination_path=input_data.destination_path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_copy(self, input_data: FileInput) -> FileResult:
        """Execute copy."""
        start = time.perf_counter()
        if not input_data.path or not input_data.destination_path:
            return FileResult(
                operation=FileOperation.COPY,
                success=False,
                error="Both path and destination_path are required for copy operation",
            )
        try:
            res = self.registry.manager_tool.copy_entity(
                source_path=input_data.path,
                destination_path=input_data.destination_path,
                overwrite=input_data.overwrite,
                create_parents=input_data.create_parents,
                dry_run=input_data.dry_run,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.COPY,
                success=res["success"],
                path=res["path"],
                destination_path=res["destination_path"],
                dry_run=res.get("dry_run", False),
                stats={"latency_ms": latency},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File copy failed from '%s' to '%s': %s", input_data.path, input_data.destination_path, err)
            return FileResult(
                operation=FileOperation.COPY,
                success=False,
                path=input_data.path,
                destination_path=input_data.destination_path,
                error=str(err),
                stats={"latency_ms": latency},
            )

    def execute_metadata(self, input_data: FileInput) -> FileResult:
        """Execute metadata inspection."""
        start = time.perf_counter()
        if not input_data.path:
            return FileResult(
                operation=FileOperation.METADATA,
                success=False,
                error="Path is required for metadata operation",
            )
        try:
            meta = self.registry.manager_tool.get_metadata(raw_path=input_data.path)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FileResult(
                operation=FileOperation.METADATA,
                success=True,
                path=meta.path,
                metadata=meta,
                stats={"latency_ms": latency},
            )
        except Exception as err:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("File metadata failed for '%s': %s", input_data.path, err)
            return FileResult(
                operation=FileOperation.METADATA,
                success=False,
                path=input_data.path,
                error=str(err),
                stats={"latency_ms": latency},
            )


__all__ = ["FileWorkflow"]
