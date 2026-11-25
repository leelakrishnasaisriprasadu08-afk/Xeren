"""Configuration settings for Xeren Sovereign Knowledge DB."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from xeren.rag.knowledge_db.schema.enums import TelemetryPrivacyPolicy


class KnowledgeDBConfig(BaseModel):
    """Configuration governing storage layout, telemetry, and reliability settings."""

    root_dir: Path = Field(
        default=Path("data/knowledge_db"),
        description="Root filesystem directory for the Knowledge DB subsystem",
    )
    telemetry_policy: TelemetryPrivacyPolicy = Field(
        default=TelemetryPrivacyPolicy.HASH_ONLY,
        description="Controls retention of user query text in retrieval telemetry",
    )
    busy_timeout_ms: int = Field(
        default=5000,
        ge=500,
        description="SQLite busy timeout in milliseconds",
    )
    wal_autocheckpoint_pages: int = Field(
        default=1000,
        ge=100,
        description="SQLite WAL autocheckpoint page count",
    )
    auto_backup_on_ingest: bool = Field(
        default=False,
        description="Whether to trigger an asynchronous snapshot checkpoint after each document ingestion",
    )

    @property
    def primary_dir(self) -> Path:
        return self.root_dir / "primary"

    @property
    def primary_db_path(self) -> Path:
        return self.primary_dir / "metadata.db"

    @property
    def primary_docs_dir(self) -> Path:
        return self.primary_dir / "documents"

    @property
    def primary_indexes_dir(self) -> Path:
        return self.primary_dir / "indexes"

    @property
    def backup_dir(self) -> Path:
        return self.root_dir / "backup"

    @property
    def backup_db_path(self) -> Path:
        return self.backup_dir / "metadata.db"

    @property
    def backup_docs_dir(self) -> Path:
        return self.backup_dir / "documents"

    @property
    def backup_indexes_dir(self) -> Path:
        return self.backup_dir / "indexes"

    @property
    def manifests_dir(self) -> Path:
        return self.root_dir / "manifests"

    @property
    def recovery_dir(self) -> Path:
        return self.root_dir / "recovery"

    def ensure_directories(self) -> None:
        """Create all subsystem directories safely."""
        self.primary_dir.mkdir(parents=True, exist_ok=True)
        self.primary_docs_dir.mkdir(parents=True, exist_ok=True)
        self.primary_indexes_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_docs_dir.mkdir(parents=True, exist_ok=True)
        self.backup_indexes_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
