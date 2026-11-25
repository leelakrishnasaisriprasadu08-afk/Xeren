"""RecoveryManager managing corruption quarantine and lossless restore from backup."""

import logging
from pathlib import Path
import shutil
import threading
import time
from typing import Optional

from xeren.rag.knowledge_db.backup.manifest import load_manifest, verify_manifest
from xeren.rag.knowledge_db.config import KnowledgeDBConfig
from xeren.rag.knowledge_db.indexing.base import IVectorIndexEngine
from xeren.rag.knowledge_db.schema.enums import HealthState
from xeren.rag.knowledge_db.storage.connection import ConnectionManager

logger = logging.getLogger("xeren.rag.knowledge_db.recovery")


class RecoveryManager:
    """Detects primary corruption, quarantines damaged files, and executes restore from backup."""

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

    def inspect_health(self) -> HealthState:
        """Evaluate operational health of primary and backup."""
        if not self.config.primary_db_path.exists():
            return HealthState.PRIMARY_CORRUPTED

        if not self.conn_mgr.quick_check():
            return HealthState.PRIMARY_CORRUPTED

        return HealthState.PRIMARY_HEALTHY

    def inspect_backup_health(self) -> HealthState:
        """Check if backup directory and manifest are valid."""
        manifest_file = self.config.manifests_dir / "latest_manifest.json"
        manifest = load_manifest(manifest_file)
        if not manifest:
            return HealthState.BACKUP_INVALID

        if not verify_manifest(manifest, self.config.backup_dir):
            return HealthState.BACKUP_INVALID

        return HealthState.BACKUP_AVAILABLE

    def restore_from_backup(self) -> bool:
        """Quarantine damaged primary and restore from latest verified backup snapshot."""
        with self._lock:
            # 1. Step 1: Verify backup is valid
            backup_state = self.inspect_backup_health()
            if backup_state != HealthState.BACKUP_AVAILABLE:
                logger.error("Restore aborted: Backup is invalid or missing.")
                return False

            # 2. Step 2: Close primary SQLite connection
            self.conn_mgr.close()

            # 3. Step 3: Quarantine damaged primary
            quarantine_dir = self.config.recovery_dir / f"quarantined_{int(time.time())}"
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            if self.config.primary_db_path.exists():
                shutil.move(str(self.config.primary_db_path), str(quarantine_dir / "metadata.db"))

            # Also quarantine WAL and SHM if present
            wal_file = self.config.primary_dir / "metadata.db-wal"
            shm_file = self.config.primary_dir / "metadata.db-shm"
            if wal_file.exists():
                shutil.move(str(wal_file), str(quarantine_dir / "metadata.db-wal"))
            if shm_file.exists():
                shutil.move(str(shm_file), str(quarantine_dir / "metadata.db-shm"))

            # 4. Step 4: Restore metadata.db from backup
            shutil.copy2(str(self.config.backup_db_path), str(self.config.primary_db_path))

            # 5. Step 5: Restore documents directory
            if self.config.backup_docs_dir.exists():
                for item in self.config.backup_docs_dir.iterdir():
                    dest = self.config.primary_docs_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    elif item.is_file():
                        shutil.copy2(item, dest)

            # 6. Step 6: Restore vector index snapshot
            vec_snap = self.config.backup_indexes_dir / "vectors_snapshot.npz"
            if vec_snap.exists():
                dest_vec = self.config.primary_indexes_dir / "vectors_snapshot.npz"
                shutil.copy2(str(vec_snap), str(dest_vec))
                self.vector_engine.restore(dest_vec)

            # 7. Step 7: Verify restored primary integrity
            if not self.conn_mgr.full_integrity_check():
                logger.critical("Restored database failed integrity check!")
                return False

            logger.info("Restore from backup completed successfully.")
            return True
