"""
Xeren ExperienceStore Causal Engine — Persistent Storage Engine
==============================================================
Thread-safe, sovereign SQLite WAL-backed authoritative storage for CausalTuples.
Includes:
- Relational table `causal_experiences` with primary key fingerprint and status indexing
- FTS5 full-text virtual index for sub-millisecond causal pattern lookups
- Automatic synchronization between relational and FTS indices
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from .models import CausalTuple, ReviewStatus

logger = logging.getLogger("xeren.core.experience.store")


class CausalExperienceStore:
    """Authoritative persistent SQLite WAL store for verified causal tuples."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or Path("data/causal_experience.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS causal_experiences (
                    fingerprint TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    root_cause TEXT,
                    new_strategy TEXT,
                    verification_score REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_causal_status_success
                ON causal_experiences(status, success);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_causal_task_id
                ON causal_experiences(task_id);
            """)

            # Full-Text Search (FTS5) for sub-millisecond similarity queries
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS causal_fts USING fts5(
                    fingerprint UNINDEXED,
                    objective,
                    action,
                    root_cause,
                    new_strategy
                );
            """)

    def save(self, item: CausalTuple) -> bool:
        """Store or update a CausalTuple with synchronized FTS indexing."""
        with self._lock, self._get_connection() as conn:
            # Upsert into relational table
            conn.execute("""
                INSERT INTO causal_experiences (
                    fingerprint, task_id, objective, action, result, success,
                    root_cause, new_strategy, verification_score, status, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    status=excluded.status,
                    verification_score=excluded.verification_score,
                    root_cause=excluded.root_cause,
                    new_strategy=excluded.new_strategy,
                    metadata_json=excluded.metadata_json;
            """, (
                item.fingerprint,
                item.task_id,
                item.objective,
                item.action,
                item.result,
                1 if item.success else 0,
                item.root_cause,
                item.new_strategy,
                item.verification_score,
                item.status.value,
                item.created_at,
                json.dumps(item.metadata),
            ))

            # Maintain FTS table
            conn.execute("DELETE FROM causal_fts WHERE fingerprint = ?;", (item.fingerprint,))
            conn.execute("""
                INSERT INTO causal_fts (fingerprint, objective, action, root_cause, new_strategy)
                VALUES (?, ?, ?, ?, ?);
            """, (
                item.fingerprint,
                item.objective,
                item.action,
                item.root_cause or "",
                item.new_strategy or "",
            ))
            return True

    def get_by_fingerprint(self, fingerprint: str) -> Optional[CausalTuple]:
        """Fetch a single causal tuple by fingerprint."""
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM causal_experiences WHERE fingerprint = ?;", (fingerprint,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_tuple(row)

    def search(
        self,
        query: str,
        success_only: Optional[bool] = None,
        approved_only: bool = True,
        limit: int = 5,
    ) -> List[CausalTuple]:
        """Fast FTS search returning matching causal tuples ranked by relevance."""
        clean_q = "".join(c if c.isalnum() else " " for c in query).strip()
        if not clean_q:
            return []

        tokens = clean_q.split()
        fts_query = " OR ".join(f'"{t}"' for t in tokens[:8])

        with self._lock, self._get_connection() as conn:
            sql = """
                SELECT e.*
                FROM causal_fts f
                JOIN causal_experiences e ON f.fingerprint = e.fingerprint
                WHERE causal_fts MATCH ?
            """
            params: List[Any] = [fts_query]

            if approved_only:
                sql += " AND e.status = ?"
                params.append(ReviewStatus.APPROVED.value)

            if success_only is not None:
                sql += " AND e.success = ?"
                params.append(1 if success_only else 0)

            sql += " ORDER BY rank LIMIT ?;"
            params.append(limit)

            try:
                rows = conn.execute(sql, params).fetchall()
                return [self._row_to_tuple(r) for r in rows]
            except sqlite3.OperationalError as e:
                logger.warning("[CausalStore] FTS query '%s' failed (%s), falling back to LIKE", fts_query, e)
                # Fallback to standard LIKE if FTS expression has syntax quirk
                fallback_sql = """
                    SELECT * FROM causal_experiences
                    WHERE (objective LIKE ? OR action LIKE ? OR root_cause LIKE ?)
                """
                like_param = f"%{tokens[0]}%"
                f_params: List[Any] = [like_param, like_param, like_param]
                if approved_only:
                    fallback_sql += " AND status = ?"
                    f_params.append(ReviewStatus.APPROVED.value)
                if success_only is not None:
                    fallback_sql += " AND success = ?"
                    f_params.append(1 if success_only else 0)
                fallback_sql += " LIMIT ?;"
                f_params.append(limit)
                rows = conn.execute(fallback_sql, f_params).fetchall()
                return [self._row_to_tuple(r) for r in rows]

    def list_all(self, status: Optional[ReviewStatus] = None, limit: int = 100) -> List[CausalTuple]:
        """List stored tuples with optional status filter."""
        with self._lock, self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM causal_experiences WHERE status = ? ORDER BY created_at DESC LIMIT ?;",
                    (status.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM causal_experiences ORDER BY created_at DESC LIMIT ?;",
                    (limit,),
                ).fetchall()
            return [self._row_to_tuple(r) for r in rows]

    def count(self, status: Optional[ReviewStatus] = None) -> int:
        """Count total records."""
        with self._lock, self._get_connection() as conn:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM causal_experiences WHERE status = ?;", (status.value,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS cnt FROM causal_experiences;").fetchone()
            return row["cnt"] if row else 0

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM causal_experiences;")
            conn.execute("DELETE FROM causal_fts;")

    @staticmethod
    def _row_to_tuple(row: sqlite3.Row) -> CausalTuple:
        return CausalTuple(
            task_id=row["task_id"],
            objective=row["objective"],
            action=row["action"],
            result=row["result"],
            success=bool(row["success"]),
            root_cause=row["root_cause"],
            new_strategy=row["new_strategy"],
            verification_score=float(row["verification_score"]),
            status=ReviewStatus(row["status"]),
            fingerprint=row["fingerprint"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
        )
