"""BackupManifest generation, validation, and SHA-256 verification."""

import hashlib
import json
from pathlib import Path
from typing import Optional

from xeren.rag.knowledge_db.schema.models import BackupManifest


def compute_file_sha256(path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    if not path.exists() or not path.is_file():
        return ""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def save_manifest(manifest: BackupManifest, target_file: Path) -> None:
    """Persist manifest to disk atomically."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = target_file.parent / f"{target_file.name}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))
    tmp_file.replace(target_file)


def load_manifest(manifest_file: Path) -> Optional[BackupManifest]:
    """Read and parse a backup manifest."""
    if not manifest_file.exists():
        return None
    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BackupManifest(**data)


def verify_manifest(manifest: BackupManifest, backup_dir: Path) -> bool:
    """Verify that backup directory contents match the manifest checksums."""
    db_file = backup_dir / "metadata.db"
    indexes_file = backup_dir / "indexes" / "vectors_snapshot.npz"

    if not db_file.exists():
        return False

    db_hash = compute_file_sha256(db_file)
    if db_hash != manifest.metadata_checksum_sha256:
        return False

    if indexes_file.exists() and manifest.indexes_checksum_sha256:
        idx_hash = compute_file_sha256(indexes_file)
        if idx_hash != manifest.indexes_checksum_sha256:
            return False

    return True
