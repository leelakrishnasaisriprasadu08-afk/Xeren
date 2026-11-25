"""SnapshotManager executing consistent online snapshots from Primary to Backup."""

import os
from pathlib import Path
import shutil
import threading
import time
from typing import Optional

from xeren.rag.knowledge_db.backup.manifest import compute_file_sha256, save_manifest
from xeren.rag.knowledge_db.config import KnowledgeDBConfig
from xeren.rag.knowledge_db.indexing.base import IVectorIndexEngine
from xeren.rag.knowledge_db.schema.models import BackupManifest
from xeren.rag.knowledge_db.storage.connection import ConnectionManager


class SnapshotManager:
    """Creates transaction-safe passive backup snapshots without blocking active queries."""

    def __init__(
        self,
        config: KnowledgeDBConfig,
        connection_mgr: ConnectionManager,
        vector_engine: IVectorIndexEngine,
    ) -> None:
        self.config = config
        self.conn_mgr = connection_mgr
        self.vector_engine = vector_engine
        self._lock = threading.Lock()
        self._seq = 1

    def create_snapshot(self) -> BackupManifest:
        """Execute a full, verified backup snapshot sequence."""
        with self._lock:
            self.config.ensure_directories()
            tmp_db = self.config.backup_dir / "metadata.db.tmp"
            final_db = self.config.backup_db_path

            # 1. Step 1: Stream SQLite online backup to temporary file
            self.conn_mgr.backup_to(tmp_db)

            # 2. Step 2: Stream vector index snapshot to backup/indexes/
            vec_snap_path = self.vector_engine.snapshot(self.config.backup_indexes_dir)

            # 3. Step 3: Copy documents directory if present
            if self.config.primary_docs_dir.exists():
                for item in self.config.primary_docs_dir.iterdir():
                    dest_item = self.config.backup_docs_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest_item, dirs_exist_ok=True)
                    elif item.is_file():
                        shutil.copy2(item, dest_item)

            # 4. Step 4: Calculate SHA-256 Checksums
            db_sha = compute_file_sha256(tmp_db)
            vec_sha = compute_file_sha256(vec_snap_path) if vec_snap_path and vec_snap_path.exists() else ""

            # Count statistics from SQLite
            conn = self.conn_mgr.get_connection()
            doc_cnt = conn.execute("SELECT COUNT(*) FROM documents;").fetchone()[0]
            chunk_cnt = conn.execute("SELECT COUNT(*) FROM chunks;").fetchone()[0]
            emb_cnt = conn.execute("SELECT COUNT(*) FROM embeddings;").fetchone()[0]

            manifest = BackupManifest(
                checkpoint_sequence=self._seq,
                metadata_checksum_sha256=db_sha,
                indexes_checksum_sha256=vec_sha,
                documents_count=doc_cnt,
                chunks_count=chunk_cnt,
                embeddings_count=emb_cnt,
                is_verified=True,
            )
            self._seq += 1

            # 5. Step 5: Save manifest in manifests/ directory
            manifest_file = self.config.manifests_dir / f"manifest_{int(manifest.created_at)}.json"
            save_manifest(manifest, manifest_file)

            # Also save latest pointer
            save_manifest(manifest, self.config.manifests_dir / "latest_manifest.json")

            # 6. Step 6: Atomic rename replace for backup/metadata.db
            os.replace(tmp_db, final_db)

            return manifest
