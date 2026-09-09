"""SQLite backend for experience storage using SQLModel."""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import Column
from sqlalchemy.types import JSON

from xeren.plugins.experience.schemas import ExperienceItem, UserFeedback
from xeren.plugins.experience.stores.base import BaseExperienceStore

class ExperienceRecord(SQLModel, table=True):
    """SQLModel table representing an ExperienceItem."""
    id: str = Field(primary_key=True)
    task: str
    context: Optional[str] = None
    selected_plugin: Optional[str] = None
    action: Optional[str] = None
    outcome: Any = Field(default=None, sa_column=Column(JSON))
    success: bool = True
    verification_status: Optional[str] = None
    verification_score: Optional[float] = None
    user_feedback: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    confidence: float = 1.0
    timestamp: datetime
    lesson: Optional[str] = None
    failure_reason: Optional[str] = None
    failure_avoidance_advice: Optional[str] = None
    error: Optional[str] = None
    is_reusable: bool = True
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    content_fingerprint: str = ""
    metadata_: Dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))

    @classmethod
    def from_item(cls, item: ExperienceItem) -> "ExperienceRecord":
        return cls(
            id=item.id,
            task=item.task,
            context=item.context,
            selected_plugin=item.selected_plugin,
            action=item.action,
            outcome=item.outcome,
            success=item.success,
            verification_status=item.verification_status,
            verification_score=item.verification_score,
            user_feedback=item.user_feedback.model_dump(mode="json") if item.user_feedback else None,
            confidence=item.confidence,
            timestamp=item.timestamp,
            lesson=item.lesson,
            failure_reason=item.failure_reason,
            failure_avoidance_advice=item.failure_avoidance_advice,
            error=item.error,
            is_reusable=item.is_reusable,
            tags=item.tags,
            content_fingerprint=item.content_fingerprint,
            metadata_=item.metadata,
        )

    def to_item(self) -> ExperienceItem:
        return ExperienceItem(
            id=self.id,
            task=self.task,
            context=self.context,
            selected_plugin=self.selected_plugin,
            action=self.action,
            outcome=self.outcome,
            success=self.success,
            verification_status=self.verification_status,
            verification_score=self.verification_score,
            user_feedback=UserFeedback(**self.user_feedback) if self.user_feedback else None,
            confidence=self.confidence,
            timestamp=self.timestamp,
            lesson=self.lesson,
            failure_reason=self.failure_reason,
            failure_avoidance_advice=self.failure_avoidance_advice,
            error=self.error,
            is_reusable=self.is_reusable,
            tags=self.tags,
            content_fingerprint=self.content_fingerprint,
            metadata=self.metadata_,
        )


class SQLiteExperienceStore(BaseExperienceStore):
    """Experience store using SQLite and SQLModel."""

    def __init__(self, db_path: str = "sqlite:///data/xeren.db"):
        import sys
        import os
        from sqlalchemy.pool import StaticPool
        
        connect_args = {"check_same_thread": False}
        kwargs = {}
        if "pytest" in sys.modules:
            db_path = "sqlite:///:memory:"
            kwargs["poolclass"] = StaticPool
        else:
            os.makedirs("data", exist_ok=True)
            
        self.engine = create_engine(db_path, connect_args=connect_args, **kwargs)
        SQLModel.metadata.create_all(self.engine)

    def add(self, item: ExperienceItem) -> str:
        with Session(self.engine) as session:
            record = ExperienceRecord.from_item(item)
            session.add(record)
            session.commit()
            return item.id

    def get(self, item_id: str) -> Optional[ExperienceItem]:
        with Session(self.engine) as session:
            record = session.get(ExperienceRecord, item_id)
            if record:
                return record.to_item()
            return None

    def get_by_fingerprint(self, fingerprint: str) -> Optional[ExperienceItem]:
        with Session(self.engine) as session:
            statement = select(ExperienceRecord).where(ExperienceRecord.content_fingerprint == fingerprint)
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
        with Session(self.engine) as session:
            statement = select(ExperienceRecord)
            if filters:
                for key, value in filters.items():
                    if hasattr(ExperienceRecord, key):
                        statement = statement.where(getattr(ExperienceRecord, key) == value)
            statement = statement.limit(limit)
            records = session.exec(statement).all()
            return [r.to_item() for r in records]

    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
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

    def delete(self, item_id: str) -> bool:
        with Session(self.engine) as session:
            record = session.get(ExperienceRecord, item_id)
            if not record:
                return False
            session.delete(record)
            session.commit()
            return True

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        with Session(self.engine) as session:
            statement = select(ExperienceRecord)
            if filters:
                for key, value in filters.items():
                    if hasattr(ExperienceRecord, key):
                        statement = statement.where(getattr(ExperienceRecord, key) == value)
            return len(session.exec(statement).all())

    def clear(self) -> None:
        with Session(self.engine) as session:
            statement = select(ExperienceRecord)
            records = session.exec(statement).all()
            for record in records:
                session.delete(record)
            session.commit()
