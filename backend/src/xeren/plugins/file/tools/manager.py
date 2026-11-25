"""File manager tool handling deletion, moves, copies, directory listing, and metadata inspection."""

from datetime import datetime, timezone
import hashlib
import logging
import mimetypes
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from xeren.plugins.file.schemas import FileItemMetadata
from xeren.plugins.file.tools.reader import FileReaderTool
from xeren.plugins.file.tools.security import FileSecurityTool

logger = logging.getLogger("xeren.plugins.file.tools.manager")


class FileManagerTool:
    """Safely manages lifecycle, listing, and inspection operations for files and folders."""

    def __init__(self, security_tool: Optional[FileSecurityTool] = None) -> None:
        self.security = security_tool or FileSecurityTool()

    def delete_entity(
        self,
        raw_path: str,
        recursive: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Safely delete a file or directory. Deletion of the workspace root is strictly blocked."""
        target_path = self.security.resolve_and_validate_path(raw_path, must_exist=True)

        # Enforce workspace root protection
        self.security.validate_not_workspace_root(target_path, operation_name="delete")
        rel_path = self.security.get_relative_path(target_path)

        if dry_run:
            logger.info("Simulated dry-run deletion for '%s'", raw_path)
            return {
                "success": True,
                "path": rel_path,
                "dry_run": True,
                "is_directory": target_path.is_dir(),
            }

        try:
            if target_path.is_dir():
                if recursive:
                    shutil.rmtree(target_path)
                else:
                    target_path.rmdir()
            else:
                target_path.unlink()
        except Exception as err:
            logger.error("Failed to delete '%s': %s", raw_path, err)
            raise OSError(f"Failed to delete '{raw_path}': {err}") from err

        return {
            "success": True,
            "path": rel_path,
            "dry_run": False,
            "is_directory": target_path.is_dir() if target_path.exists() else False,
        }

    def move_entity(
        self,
        source_path: str,
        destination_path: str,
        overwrite: bool = False,
        create_parents: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Move or rename a file or directory within workspace boundaries."""
        src = self.security.resolve_and_validate_path(source_path, must_exist=True)
        self.security.validate_not_workspace_root(src, operation_name="move source")

        dst = self.security.resolve_and_validate_path(destination_path, must_exist=False)
        self.security.validate_not_workspace_root(dst, operation_name="move destination")

        if dst.exists() and not overwrite:
            raise FileExistsError(
                f"Destination path '{destination_path}' already exists and overwrite is False"
            )

        src_rel = self.security.get_relative_path(src)
        dst_rel = self.security.get_relative_path(dst)

        if dry_run:
            logger.info("Simulated dry-run move from '%s' to '%s'", source_path, destination_path)
            return {
                "success": True,
                "path": src_rel,
                "destination_path": dst_rel,
                "dry_run": True,
            }

        if create_parents and not dst.parent.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists() and overwrite:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()

        shutil.move(str(src), str(dst))

        return {
            "success": True,
            "path": src_rel,
            "destination_path": dst_rel,
            "dry_run": False,
        }

    def copy_entity(
        self,
        source_path: str,
        destination_path: str,
        overwrite: bool = False,
        create_parents: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Copy a file or directory tree within workspace boundaries."""
        src = self.security.resolve_and_validate_path(source_path, must_exist=True)
        dst = self.security.resolve_and_validate_path(destination_path, must_exist=False)
        self.security.validate_not_workspace_root(dst, operation_name="copy destination")

        if dst.exists() and not overwrite:
            raise FileExistsError(
                f"Destination path '{destination_path}' already exists and overwrite is False"
            )

        src_rel = self.security.get_relative_path(src)
        dst_rel = self.security.get_relative_path(dst)

        if dry_run:
            logger.info("Simulated dry-run copy from '%s' to '%s'", source_path, destination_path)
            return {
                "success": True,
                "path": src_rel,
                "destination_path": dst_rel,
                "dry_run": True,
            }

        if create_parents and not dst.parent.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            if dst.exists() and overwrite:
                shutil.rmtree(dst)
            shutil.copytree(str(src), str(dst), dirs_exist_ok=overwrite)
        else:
            if dst.exists() and overwrite:
                dst.unlink()
            shutil.copy2(str(src), str(dst))

        return {
            "success": True,
            "path": src_rel,
            "destination_path": dst_rel,
            "dry_run": False,
        }

    def list_directory(
        self,
        raw_path: Optional[str] = None,
        pattern: Optional[str] = None,
        recursive: bool = True,
        include_hidden: bool = False,
        max_results: int = 100,
    ) -> List[FileItemMetadata]:
        """List files and folders within a target workspace directory."""
        target_dir = (
            self.security.resolve_and_validate_path(raw_path, must_exist=True)
            if raw_path
            else self.security.workspace_dir
        )

        if not target_dir.is_dir():
            raise NotADirectoryError(f"Target path '{raw_path or '.'}' is not a directory")

        results: List[FileItemMetadata] = []
        glob_pat = pattern or "*"

        iterator = target_dir.rglob(glob_pat) if recursive else target_dir.glob(glob_pat)

        for item in iterator:
            if len(results) >= max_results:
                break

            # Filter out hidden files unless requested
            if not include_hidden and any(part.startswith(".") for part in item.relative_to(target_dir).parts):
                continue

            # Verify item resides within workspace
            try:
                meta = self.get_metadata(self.security.get_relative_path(item))
                results.append(meta)
            except Exception as err:
                logger.debug("Skipping item '%s' during list: %s", item, err)
                continue

        return results

    def get_metadata(self, raw_path: str) -> FileItemMetadata:
        """Retrieve rich structural metadata for a file or directory."""
        target_path = self.security.resolve_and_validate_path(raw_path, must_exist=True)
        stat = target_path.stat()

        is_dir = target_path.is_dir()
        is_file = target_path.is_file()
        is_symlink = target_path.is_symlink()
        size_bytes = stat.st_size if is_file else 0

        created_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
        modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        permissions_str = oct(stat.st_mode)[-3:]

        mime_type, _ = mimetypes.guess_type(target_path.name)
        is_binary = FileReaderTool.is_binary_file(target_path) if is_file else False

        checksum = None
        if is_file and size_bytes <= self.security.max_file_size_bytes:
            try:
                hasher = hashlib.sha256()
                with open(target_path, "rb") as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
                checksum = hasher.hexdigest()
            except Exception:
                checksum = None

        return FileItemMetadata(
            path=self.security.get_relative_path(target_path),
            name=target_path.name,
            size_bytes=size_bytes,
            is_directory=is_dir,
            is_file=is_file,
            is_symlink=is_symlink,
            extension=target_path.suffix,
            mime_type=mime_type,
            is_binary=is_binary,
            created_at=created_dt,
            modified_at=modified_dt,
            permissions=permissions_str,
            checksum_sha256=checksum,
        )


__all__ = ["FileManagerTool"]
