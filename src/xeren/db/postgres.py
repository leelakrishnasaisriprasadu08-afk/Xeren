"""PostgreSQL Connection Manager & Engine Provider for Xeren.

Supports Supabase, Neon, AWS RDS, and local PostgreSQL instances,
providing live connection verification (ping latency, version, schema tables)
with safe credential masking and SQLModel / SQLAlchemy engine pooling.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("xeren.db.postgres")

try:
    import psycopg2  # type: ignore[import-untyped]
    from sqlmodel import create_engine, text
    from sqlalchemy.engine import Engine
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    Engine = Any  # type: ignore


class PostgresConnectionManager:
    """Manages PostgreSQL connections, engine lifecycle, pooling, and telemetry."""

    def __init__(self, default_uri: Optional[str] = None) -> None:
        self.uri = default_uri if default_uri is not None else (os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URI", ""))
        self._engine: Optional[Engine] = None
        self._connected = False
        self._last_ping_ms: Optional[float] = None
        self._last_checked_at: Optional[str] = None
        self._server_version: Optional[str] = None
        self._database_name: Optional[str] = None
        self._tables: List[str] = []

        if self.uri and PSYCOPG2_AVAILABLE:
            self.verify_connection(self.uri)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _normalize_driver_uri(self, uri: str) -> str:
        """Ensure connection string starts with postgresql+psycopg2:// for SQLModel/SQLAlchemy."""
        if uri.startswith("postgres://"):
            return "postgresql+psycopg2://" + uri[len("postgres://") :]
        if uri.startswith("postgresql://") and not uri.startswith("postgresql+"):
            return "postgresql+psycopg2://" + uri[len("postgresql://") :]
        return uri

    def _raw_connection_uri(self, uri: str) -> str:
        """Strip SQLModel dialect prefix for raw psycopg2.connect calls."""
        if uri.startswith("postgresql+psycopg2://"):
            return "postgresql://" + uri[len("postgresql+psycopg2://") :]
        return uri

    def get_engine(self) -> Optional[Engine]:
        """Return cached SQLAlchemy/SQLModel Engine with robust connection pooling."""
        if not PSYCOPG2_AVAILABLE or not self.uri:
            return None

        if self._engine is None:
            normalized_uri = self._normalize_driver_uri(self.uri)
            self._engine = create_engine(
                normalized_uri,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    def verify_connection(
        self,
        uri: Optional[str] = None,
        timeout_seconds: int = 5,
    ) -> Dict[str, Any]:
        """Test and verify PostgreSQL connectivity, measuring ping latency and schema info."""
        target_uri = uri if uri is not None else self.uri

        if not target_uri:
            self._connected = False
            return {
                "connected": False,
                "mode": "unconfigured",
                "message": "No PostgreSQL connection URI configured (set DATABASE_URL in .env).",
                "database": None,
                "latency_ms": None,
                "server_version": None,
                "tables": [],
            }

        if not PSYCOPG2_AVAILABLE:
            self._connected = False
            return {
                "connected": False,
                "mode": "missing_driver",
                "message": "psycopg2 package is not installed in the environment.",
                "database": None,
                "latency_ms": None,
                "server_version": None,
                "tables": [],
            }

        raw_uri = self._raw_connection_uri(target_uri)

        try:
            start_time = time.perf_counter()
            conn = psycopg2.connect(raw_uri, connect_timeout=timeout_seconds)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), version();")
                row = cur.fetchone()
                db_name = row[0] if row else "postgres"
                full_version = row[1] if row else "Unknown"

                # Fetch table names from public schema
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """)
                tables = [r[0] for r in cur.fetchall()]

            conn.close()

            # Cache successful state
            self.uri = target_uri
            self._connected = True
            self._last_ping_ms = elapsed_ms
            self._last_checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._server_version = full_version.split(" on ")[0] if " on " in full_version else full_version
            self._database_name = db_name
            self._tables = tables

            # Reset engine if URI changed
            self._engine = None

            logger.info("PostgreSQL successfully verified: db=%s, latency=%.2fms", db_name, elapsed_ms)
            return {
                "connected": True,
                "mode": "cloud_postgres" if "supabase" in target_uri or "neon" in target_uri else "postgres",
                "message": f"Connected to PostgreSQL ({db_name}) successfully.",
                "database": db_name,
                "latency_ms": elapsed_ms,
                "server_version": self._server_version,
                "tables": tables,
                "checked_at": self._last_checked_at,
            }
        except Exception as exc:
            self._connected = False
            logger.warning("PostgreSQL connection verification failed: %s", exc)
            return {
                "connected": False,
                "mode": "error",
                "message": f"Connection check failed ({type(exc).__name__}): {exc}",
                "database": None,
                "latency_ms": None,
                "server_version": None,
                "tables": [],
                "error": str(exc),
            }

    def get_status(self) -> Dict[str, Any]:
        """Return cached status of PostgreSQL connectivity for health checks and UI display."""
        return {
            "connected": self._connected,
            "database": self._database_name,
            "latency_ms": self._last_ping_ms,
            "server_version": self._server_version,
            "tables": self._tables,
            "last_checked_at": self._last_checked_at,
            "uri_configured": bool(self.uri),
            "masked_uri": self._mask_uri(self.uri) if self.uri else None,
        }

    def _mask_uri(self, uri: str) -> str:
        """Mask password in PostgreSQL connection URI for safe telemetry/UI presentation."""
        try:
            if "@" in uri:
                prefix, suffix = uri.split("@", 1)
                if "://" in prefix:
                    scheme, user_info = prefix.split("://", 1)
                    if ":" in user_info:
                        user = user_info.split(":", 1)[0]
                        return f"{scheme}://{user}:••••••••@{suffix}"
                return f"postgresql://••••:••••@{suffix}"
            return uri
        except Exception:
            return "postgresql://••••••••"


# Global singleton instance
postgres_manager = PostgresConnectionManager()
