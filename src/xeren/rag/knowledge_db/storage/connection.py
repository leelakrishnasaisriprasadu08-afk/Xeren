"""SQLite connection provider with WAL mode and transaction safeguards."""

from contextlib import contextmanager
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Generator, Optional

from xeren.rag.knowledge_db.config import KnowledgeDBConfig
from xeren.rag.knowledge_db.schema.ddl import init_schema

logger = logging.getLogger("xeren.rag.knowledge_db.storage")


class ConnectionManager:
    """Manages thread-safe SQLite connections with WAL mode and health checks."""

    def __init__(self, db_path: Path, config: Optional[KnowledgeDBConfig] = None) -> None:
        self.db_path = db_path
        self.config = config or KnowledgeDBConfig()
        self._lock = threading.RLock()
        self._local = threading.local()
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Ensure database file exists and schema is initialized."""
        with self._lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = self._create_connection()
            try:
                init_schema(conn)
            finally:
                conn.close()

    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection with WAL pragmas."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=float(self.config.busy_timeout_ms) / 1000.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute(f"PRAGMA wal_autocheckpoint = {self.config.wal_autocheckpoint_pages};")
        except sqlite3.DatabaseError:
            pass
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()
        return self._local.conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an atomic transaction."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def quick_check(self) -> bool:
        """Perform PRAGMA quick_check to verify database integrity."""
        try:
            conn = self.get_connection()
            cursor = conn.execute("PRAGMA quick_check;")
            row = cursor.fetchone()
            return row is not None and row[0].lower() == "ok"
        except Exception as e:
            logger.error("Database quick_check failed: %s", e)
            return False

    def full_integrity_check(self) -> bool:
        """Perform PRAGMA integrity_check for deep verification."""
        try:
            conn = self.get_connection()
            cursor = conn.execute("PRAGMA integrity_check;")
            rows = cursor.fetchall()
            return len(rows) == 1 and rows[0][0].lower() == "ok"
        except Exception as e:
            logger.error("Database full integrity check failed: %s", e)
            return False

    def backup_to(self, target_db_path: Path) -> None:
        """Perform online, transaction-safe backup using sqlite3_backup API."""
        with self._lock:
            target_db_path.parent.mkdir(parents=True, exist_ok=True)
            source_conn = self.get_connection()
            dest_conn = sqlite3.connect(str(target_db_path))
            try:
                source_conn.backup(dest_conn)
            finally:
                dest_conn.close()

    def close(self) -> None:
        """Close thread-local connection if open."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None
