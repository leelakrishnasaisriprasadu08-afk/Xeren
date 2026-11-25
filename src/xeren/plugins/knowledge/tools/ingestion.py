"""Ingestion tool wrapping existing Xeren IngestionPipeline."""

import logging
from typing import Any, Dict, List, Optional

from xeren.rag.document import Document
from xeren.rag.pipeline import IngestionPipeline

logger = logging.getLogger("xeren.plugins.knowledge.tools.ingestion")


class KnowledgeIngestionTool:
    """Delegates ingestion and chunk indexing directly to existing Xeren IngestionPipeline."""

    def __init__(self, pipeline: IngestionPipeline) -> None:
        self.pipeline = pipeline

    def ingest_documents(self, documents: List[Document]) -> List[str]:
        """Ingest pre-parsed Document objects through the existing pipeline."""
        return self.pipeline.index_documents(documents)

    def ingest_text(
        self,
        text: str,
        source: str = "knowledge_ingest",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Ingest raw text through the existing pipeline."""
        return self.pipeline.index_text(
            text=text,
            source=source,
            extra=metadata or {},
        )

    def ingest_batch(
        self,
        texts: Optional[List[str]] = None,
        documents: Optional[List[Document]] = None,
        source: str = "knowledge_ingest",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Ingest a batch of documents and/or raw text strings."""
        inserted_ids: List[str] = []
        if documents:
            inserted_ids.extend(self.ingest_documents(documents))
        if texts:
            for text in texts:
                inserted_ids.extend(self.ingest_text(text=text, source=source, metadata=metadata))
        return inserted_ids


__all__ = ["KnowledgeIngestionTool"]
