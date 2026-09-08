"""Immutable security audit trail — every sensitive data access is logged."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from xeren.security.schemas import AccessOutcome, AuditEvent, DataSensitivityTier

logger = logging.getLogger("xeren.security.audit")


class SecurityAuditLogger:
    """
    Logs every access attempt to Sensitive and More Sensitive data.

    Design:
    - Immutable records: no UPDATE or DELETE on audit rows
    - Path is stored as SHA-256 hash (never raw path for privacy)
    - User can read their own audit log
    - Liberal tier accesses are NOT logged (performance)
    """

    def __init__(self, db_path: str = "data/xeren.db") -> None:
        self._db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_audit_log (
                    event_id         TEXT PRIMARY KEY,
                    timestamp        TEXT NOT NULL,
                    user_id          TEXT NOT NULL,
                    path_hash        TEXT NOT NULL,
                    tier             TEXT NOT NULL,
                    operation        TEXT NOT NULL,
                    outcome          TEXT NOT NULL,
                    reason           TEXT,
                    layers_evaluated TEXT,
                    metadata         TEXT
                )
            """)
            # Index for fast user-scoped queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user
                ON security_audit_log (user_id, timestamp DESC)
            """)
            conn.commit()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(self, event: AuditEvent) -> None:
        """Record a security event. Liberal tier events are skipped."""
        if event.tier == DataSensitivityTier.LIBERAL:
            return  # Skip liberal — too noisy, no security value

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("""
                    INSERT INTO security_audit_log
                    (event_id, timestamp, user_id, path_hash, tier,
                     operation, outcome, reason, layers_evaluated, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.user_id,
                    event.path_hash,
                    event.tier.value,
                    event.operation,
                    event.outcome.value,
                    event.reason,
                    json.dumps(event.layers_evaluated),
                    json.dumps(event.metadata),
                ))
                conn.commit()
        except Exception as exc:
            logger.error("Failed to write audit log: %s", exc)

    def log_access(
        self,
        user_id: str,
        path: str,
        tier: DataSensitivityTier,
        operation: str,
        outcome: AccessOutcome,
        reason: str = "",
        layers_evaluated: Optional[List[int]] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Convenience method — hashes path and creates AuditEvent."""
        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()
        event = AuditEvent(
            user_id=user_id,
            path_hash=path_hash,
            tier=tier,
            operation=operation,
            outcome=outcome,
            reason=reason,
            layers_evaluated=layers_evaluated or [],
            metadata=metadata or {},
        )
        self.log(event)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def get_audit_log(
        self,
        user_id: str,
        last_n: int = 100,
        tier_filter: Optional[DataSensitivityTier] = None,
    ) -> List[AuditEvent]:
        """
        Retrieve recent audit events for a user.

        Args:
            user_id: Filter to this user's events only.
            last_n: Return at most this many events.
            tier_filter: Optionally filter to a specific tier.
        """
        query = """
            SELECT event_id, timestamp, user_id, path_hash, tier,
                   operation, outcome, reason, layers_evaluated, metadata
            FROM security_audit_log
            WHERE user_id = ?
        """
        params: list = [user_id]

        if tier_filter:
            query += " AND tier = ?"
            params.append(tier_filter.value)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(last_n)

        events: List[AuditEvent] = []
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        for row in rows:
            try:
                events.append(AuditEvent(
                    event_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    user_id=row[2],
                    path_hash=row[3],
                    tier=DataSensitivityTier(row[4]),
                    operation=row[5],
                    outcome=AccessOutcome(row[6]),
                    reason=row[7] or "",
                    layers_evaluated=json.loads(row[8] or "[]"),
                    metadata=json.loads(row[9] or "{}"),
                ))
            except Exception as exc:
                logger.warning("Failed to parse audit row: %s", exc)

        return events

    def export_audit_log_json(self, user_id: str) -> str:
        """Export audit log as JSON string for user review / download."""
        events = self.get_audit_log(user_id, last_n=1000)
        return json.dumps(
            [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat(),
                    "tier": e.tier.value,
                    "operation": e.operation,
                    "outcome": e.outcome.value,
                    "reason": e.reason,
                }
                for e in events
            ],
            indent=2,
        )

    def get_denied_count(self, user_id: str, hours: int = 24) -> int:
        """Return count of denied access attempts in the last N hours — for anomaly detection."""
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("""
                SELECT COUNT(*) FROM security_audit_log
                WHERE user_id = ? AND outcome = 'denied' AND timestamp >= ?
            """, (user_id, since)).fetchone()
        return row[0] if row else 0


__all__ = ["SecurityAuditLogger"]
