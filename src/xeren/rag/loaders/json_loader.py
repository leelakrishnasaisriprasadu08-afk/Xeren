"""JSON and JSONL document loader."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from xeren.rag.document import Document, DocumentMetadata
from xeren.rag.errors import DocumentLoadingError
from xeren.rag.loaders.base import BaseDocumentLoader


class JSONLoader(BaseDocumentLoader):
    """Loads .json and .jsonl files."""

    SUPPORTED_EXTENSIONS = {".json", ".jsonl"}

    def __init__(
        self,
        content_key: Optional[str] = None,
        metadata_keys: Optional[List[str]] = None,
    ) -> None:
        self.content_key = content_key
        self.metadata_keys = metadata_keys

    def supports(self, source: Union[str, Path]) -> bool:
        return Path(source).suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _item_to_document(
        self,
        item: Any,
        source_path: Path,
        index: Optional[int] = None,
    ) -> Document:
        if isinstance(item, dict):
            if self.content_key and self.content_key in item:
                content = str(item[self.content_key])
            elif "text" in item:
                content = str(item["text"])
            elif "content" in item:
                content = str(item["content"])
            else:
                content = json.dumps(item, indent=2)

            extra: Dict[str, Any] = {}
            if self.metadata_keys:
                for k in self.metadata_keys:
                    if k in item:
                        extra[k] = item[k]
            else:
                extra = {k: v for k, v in item.items() if k not in (self.content_key or ["text", "content"])}
        else:
            content = str(item)
            extra = {}

        if index is not None:
            extra["record_index"] = index

        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        meta = DocumentMetadata(
            source=str(source_path.resolve()),
            title=f"{source_path.stem}_{index}" if index is not None else source_path.stem,
            checksum=checksum,
            mime_type="application/json",
            extra=extra,
        )
        return Document(content=content, metadata=meta, doc_type="json")

    def load(self, source: Union[str, Path]) -> List[Document]:
        path = Path(source)
        if not path.is_file():
            raise DocumentLoadingError(f"File not found: {source}")

        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception as err:
            raise DocumentLoadingError(f"Failed to read JSON file {path}: {err}", raw_error=err) from err

        docs: List[Document] = []
        if path.suffix.lower() == ".jsonl":
            for idx, line in enumerate(raw_text.splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    docs.append(self._item_to_document(data, path, index=idx))
                except json.JSONDecodeError as err:
                    raise DocumentLoadingError(
                        f"Failed parsing JSONL line {idx} in {path}: {err}", raw_error=err
                    ) from err
        else:
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError as err:
                raise DocumentLoadingError(f"Failed parsing JSON in {path}: {err}", raw_error=err) from err

            if isinstance(data, list):
                for idx, item in enumerate(data):
                    docs.append(self._item_to_document(item, path, index=idx))
            else:
                docs.append(self._item_to_document(data, path))

        return docs
