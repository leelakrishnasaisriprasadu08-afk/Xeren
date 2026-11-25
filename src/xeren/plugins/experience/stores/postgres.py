"""PostgreSQL adapter for persistent experience and adaptive telemetry storage."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

try:
    from sqlmodel import Session, SQLModel, create_engine, select
    SQLMODEL_AVAILABLE = True
except ImportError:
    SQLMODEL_AVAILABLE = False
    Session = Any  # type: ignore
    SQLModel = object  # type: ignore
    create_engine = None  # type: ignore
    select = None  # type: ignore

from xeren.plugins.experience.schemas import ExperienceItem, UserFeedback
from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.stores.sqlite import ExperienceRecord

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("xeren.plugins.experience.stores.postgres")


class PostgresExperienceStore(BaseExperienceStore):
    """Production PostgreSQL adapter for Xeren experience and feedback persistence."""

    def __init__(
        self,
        connection_uri: Optional[str] = None,
        auto_create_tables: bool = True,
    ) -> None:
        self.uri = connection_uri or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URI", "")

        normalized_uri = self._normalize_uri(self.uri)
        if "sqlite" in normalized_uri:
            sqlite_kwargs: Dict[str, Any] = {"connect_args": {"check_same_thread": False}}
            if ":memory:" in normalized_uri:
                from sqlalchemy.pool import StaticPool
                sqlite_kwargs["poolclass"] = StaticPool
            self.engine = create_engine(normalized_uri, **sqlite_kwargs)
        else:
            self.engine = create_engine(
                normalized_uri,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )

        if auto_create_tables:
            try:
                SQLModel.metadata.create_all(self.engine)
                logger.info("PostgreSQL experience tables successfully initialized.")
            except Exception as e:
                logger.warning("Failed to auto-create PostgreSQL tables: %s", e)

    def _normalize_uri(self, uri: str) -> str:
        """Ensure connection string starts with postgresql+psycopg2:// for SQLModel/SQLAlchemy."""
        if not uri:
            return "sqlite:///data/xeren.db"
        if uri.startswith("postgres://"):
            return "postgresql+psycopg2://" + uri[len("postgres://") :]
        if uri.startswith("postgresql://") and not uri.startswith("postgresql+"):
            return "postgresql+psycopg2://" + uri[len("postgresql://") :]
        return uri

    def add(self, item: ExperienceItem) -> str:
        """Add a new experience item to PostgreSQL."""
        with Session(self.engine) as session:
            record = ExperienceRecord.from_item(item)
            session.add(record)
            session.commit()
            return item.id

    def get(self, item_id: str) -> Optional[ExperienceItem]:
        """Fetch an experience item by ID from PostgreSQL."""
        with Session(self.engine) as session:
            record = session.get(ExperienceRecord, item_id)
            if record:
                return record.to_item()
            return None

    def get_by_fingerprint(self, fingerprint: str) -> Optional[ExperienceItem]:
        """Fetch an experience item by content fingerprint."""
        with Session(self.engine) as session:
            statement = select(ExperienceRecord).where(
                ExperienceRecord.content_fingerprint == fingerprint
            )
            record = session.exec(statement).first()
            if record:
                return record.to_item()
            return None

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[ExperienceItem]:
        """Search experiences in PostgreSQL with filtering."""
        with Session(self.engine) as session:
            statement = select(ExperienceRecord)
            if filters:
                for key, value in filters.items():
                    if hasattr(ExperienceRecord, key):
                        statement = statement.where(getattr(ExperienceRecord, key) == value)
            statement = statement.limit(limit)
            records = session.exec(statement).all()

            items = [r.to_item() for r in records]
            if query:
                q_lower = query.lower()
                items = [
                    it
                    for it in items
                    if q_lower in it.task.lower()
                    or (it.lesson and q_lower in it.lesson.lower())
                    or (it.context and q_lower in it.context.lower())
                ]
            return items

    def update_feedback(
        self,
        item_id: str,
        score: float,
        feedback: Optional[str] = None,
        correction: Optional[str] = None,
    ) -> bool:
        """Update user feedback on an experience record."""
        with Session(self.engine) as session:
            record = session.get(ExperienceRecord, item_id)
            if not record:
                return False

            fb = record.user_feedback or {}
            fb["score"] = score
            if feedback:
                fb["feedback"] = feedback
            if correction:
                fb["correction"] = correction
            record.user_feedback = fb
            session.add(record)
            session.commit()
            return True

    def delete(self, item_id: str) -> bool:
        """Delete an experience item by ID."""
        with Session(self.engine) as session:
            record = session.get(ExperienceRecord, item_id)
            if not record:
                return False
            session.delete(record)
            session.commit()
            return True

    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update fields of an existing experience record."""
        with Session(self.engine) as session:
            record = session.get(ExperienceRecord, item_id)
            if not record:
                return False
            for key, value in updates.items():
                if key == "metadata":
                    key = "metadata_"
                if key == "user_feedback":
                    if isinstance(value, UserFeedback):
                        value = value.model_dump(mode="json")
                    elif isinstance(value, dict):
                        value = UserFeedback(**value).model_dump(mode="json")
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()
            return True

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total experiences matching optional filters in PostgreSQL."""
        with Session(self.engine) as session:
            statement = select(ExperienceRecord)
            if filters:
                for key, value in filters.items():
                    if hasattr(ExperienceRecord, key):
                        statement = statement.where(getattr(ExperienceRecord, key) == value)
            return len(session.exec(statement).all())

    def clear(self) -> None:
        """Wipe all experience records from PostgreSQL."""
        with Session(self.engine) as session:
            statement = select(ExperienceRecord)
            records = session.exec(statement).all()
            for record in records:
                session.delete(record)
            session.commit()
