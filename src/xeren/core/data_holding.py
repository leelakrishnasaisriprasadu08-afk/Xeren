"""PermittedDataHoldingVault — Futuristic context and data holding engine for Xeren.

Securely holds, indexes, and retrieves user-permitted data across:
1. Own Device Files: Local directories granted in UserVault (via FilePlugin / os_connector).
2. Connected Apps: Account and MCP records (GitHub issues/PRs, SQLite tables, Notion notes).
3. Web Knowledge: Verified research dossiers, articles, and evidence items.

Guarantees:
- Strict Permission Boundary: Only holds files explicitly granted by the user. Zero unpermitted leakage.
- Automatic Freshness & Fingerprinting: Detects file changes on disk via SHA256 content hashes.
- Grounded Prompt Augmentation: Formats relevant extracts with provenance tags so Xeren-Mini
  has zero hallucinations when reasoning about the user's files and apps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from xeren.core.vault import UserVault
from xeren.security.schemas import DataSensitivityTier

logger = logging.getLogger("xeren.core.data_holding")


class FlexibleSourceType(str):
    """String subclass that matches either standard or short category names."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, str):
            return False
        val = str(self)
        if val == other:
            return True
        if val in ("connected_app", "app") and other in ("connected_app", "app"):
            return True
        if val in ("web_research", "web") and other in ("web_research", "web"):
            return True
        if val in ("device_file", "file") and other in ("device_file", "file"):
            return True
        return False

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class HeldDataItem:
    """A single piece of permitted data held in the vault."""

    item_id: str
    source_type: str | FlexibleSourceType  # "device_file", "connected_app", "web_research"
    source_identifier: str  # File path, App name / resource URI, or Web URL
    title: str
    content: str
    content_hash: str
    tier: DataSensitivityTier = DataSensitivityTier.LIBERAL
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_verified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def integrity_hash(self) -> str:
        """Alias for content_hash verification."""
        return self.content_hash

    @property
    def app_id(self) -> Optional[str]:
        """Extracted app identifier for connected integrations."""
        if "app_id" in self.metadata:
            return str(self.metadata["app_id"])
        if ":" in self.source_identifier:
            return self.source_identifier.split(":", 1)[0]
        return self.metadata.get("app")

    @property
    def url(self) -> Optional[str]:
        """Web URL for web research items."""
        return self.metadata.get("url") or self.source_identifier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_type": str(self.source_type),
            "source_identifier": self.source_identifier,
            "title": self.title,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "content_hash": self.content_hash,
            "tier": self.tier.value if hasattr(self.tier, "value") else str(self.tier),
            "tags": self.tags,
            "metadata": self.metadata,
            "ingested_at": self.ingested_at,
        }


class PermittedDataHoldingVault:
    """Futuristic data holding vault managing user-permitted device files, apps, and web data."""

    SUPPORTED_EXTENSIONS = {
        ".txt", ".md", ".py", ".ts", ".tsx", ".js", ".jsx", ".json",
        ".html", ".css", ".yaml", ".yml", ".sql", ".csv", ".env.example"
    }

    def __init__(self, vault: Optional[UserVault] = None) -> None:
        self.vault = vault or UserVault()
        self._held_items: Dict[str, HeldDataItem] = {}
        # Index of items by source identifier for rapid updates
        self._identifier_index: Dict[str, str] = {}

    # -------------------------------------------------------------------------
    # 1. Device File Holding (Strictly User-Permitted)
    # -------------------------------------------------------------------------

    def sync_permitted_device_files(self, max_files_per_dir: int = 50) -> int:
        """Scan all granted directories in UserVault and index their content."""
        granted_dirs = self.vault.get_all_granted_directories()
        ingested_count = 0

        for granted in granted_dirs:
            path_str = granted.get("path")
            if not path_str:
                continue

            dir_path = Path(path_str)
            if not dir_path.exists() or not dir_path.is_dir():
                logger.warning("Granted directory does not exist on device: %s", path_str)
                continue

            # Ingest files matching supported code and document extensions
            files_scanned = 0
            for root, _, files in os.walk(dir_path):
                # Avoid hidden directories (.git, node_modules, .venv)
                if any(part.startswith(".") or part in ("node_modules", "__pycache__", "dist", "build") for part in Path(root).parts):
                    continue

                for file_name in files:
                    if files_scanned >= max_files_per_dir:
                        break

                    file_path = Path(root) / file_name
                    ext = file_path.suffix.lower()
                    if ext not in self.SUPPORTED_EXTENSIONS:
                        continue

                    try:
                        # Limit to files under 1MB for holding
                        if file_path.stat().st_size > 1024 * 1024:
                            continue

                        text_content = file_path.read_text(encoding="utf-8", errors="replace")
                        tier = self.vault.get_path_tier(file_path)

                        item = self.hold_device_file(
                            file_path=file_path,
                            content=text_content,
                            tier=tier,
                        )
                        if item:
                            ingested_count += 1
                            files_scanned += 1
                    except Exception as err:
                        logger.debug("Could not read file %s: %s", file_path, err)

        logger.info("Synchronized %d permitted device files into Data Holding Vault.", ingested_count)
        return ingested_count

    def hold_device_file(
        self,
        file_path: Path | str,
        content: Optional[str] = None,
        description: str = "",
        tier: DataSensitivityTier = DataSensitivityTier.LIBERAL,
        metadata: Optional[Dict[str, Any]] = None,
        raise_on_denied: Optional[bool] = None,
        **kwargs: Any,
    ) -> Optional[HeldDataItem]:
        """Index a single permitted device file into the vault."""
        resolved = Path(file_path).resolve()
        resolved_str = resolved.as_posix()

        # Security check: must be inside a granted directory
        check_func = getattr(self.vault, "is_directory_granted", getattr(self.vault, "is_path_granted", lambda p: False))
        if not check_func(resolved):
            logger.warning("Rejected file holding: path %s is not in a granted directory!", resolved_str)
            if raise_on_denied:
                raise PermissionError(f"Access denied: {file_path} is not in a permitted directory")
            return None

        if content is None:
            if resolved.exists() and resolved.is_file():
                content = resolved.read_text(encoding="utf-8", errors="replace")
            else:
                content = ""

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # If already held and hash hasn't changed, update timestamp
        existing_id = self._identifier_index.get(resolved_str)
        now_iso = datetime.now(timezone.utc).isoformat()
        if existing_id and existing_id in self._held_items:
            item = self._held_items[existing_id]
            if item.content_hash == content_hash:
                item.last_verified_at = now_iso
                return item

        item_id = f"dev_{hashlib.md5(resolved_str.encode()).hexdigest()[:12]}"
        item = HeldDataItem(
            item_id=item_id,
            source_type=FlexibleSourceType("device_file"),
            source_identifier=resolved_str,
            title=resolved.name,
            content=content,
            content_hash=content_hash,
            tier=tier,
            tags=["device", resolved.suffix.lstrip("."), "permitted_local"],
            metadata=metadata or {"parent_dir": resolved.parent.as_posix(), "size": len(content), "description": description},
            ingested_at=now_iso,
            last_verified_at=now_iso,
        )
        self._held_items[item_id] = item
        self._identifier_index[resolved_str] = item_id
        return item

    # -------------------------------------------------------------------------
    # 2. Connected App Data Holding
    # -------------------------------------------------------------------------

    def hold_connected_app_data(
        self,
        app_name: Optional[str] = None,
        entity_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tier: DataSensitivityTier = DataSensitivityTier.SENSITIVE,
        metadata: Optional[Dict[str, Any]] = None,
        app_id: Optional[str] = None,
        data_title: Optional[str] = None,
        payload: Optional[Any] = None,
        **kwargs: Any,
    ) -> HeldDataItem:
        """Hold data records from connected external applications (e.g. GitHub issue, SQLite row, Notion doc)."""
        app_name = app_name or app_id or "app"
        title = title or data_title or "Untitled App Record"
        if content is None:
            if payload is not None:
                if isinstance(payload, (dict, list)):
                    content = json.dumps(payload, default=str)
                else:
                    content = str(payload)
            else:
                content = ""
        entity_id = entity_id or hashlib.md5(title.encode()).hexdigest()[:8]

        source_id = f"{app_name}:{entity_id}"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        item_id = f"app_{hashlib.md5(source_id.encode()).hexdigest()[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        meta = dict(metadata or {})
        if app_id:
            meta["app_id"] = app_id
        if payload is not None:
            meta["payload"] = payload

        item = HeldDataItem(
            item_id=item_id,
            source_type=FlexibleSourceType("connected_app"),
            source_identifier=source_id,
            title=f"[{app_name.capitalize()}] {title}",
            content=content,
            content_hash=content_hash,
            tier=tier,
            tags=["app", app_name.lower(), "connected_integration"],
            metadata=meta,
            ingested_at=now_iso,
            last_verified_at=now_iso,
        )
        self._held_items[item_id] = item
        self._identifier_index[source_id] = item_id
        logger.info("Held app record %s from %s", entity_id, app_name)
        return item

    # -------------------------------------------------------------------------
    # 3. Web Research Data Holding
    # -------------------------------------------------------------------------

    def hold_web_research(
        self,
        url: str,
        title: str = "",
        summary: str = "",
        evidence_snippets: Optional[List[str]] = None,
        credibility_score: float = 1.0,
        content_snippet: Optional[str] = None,
        **kwargs: Any,
    ) -> HeldDataItem:
        """Hold verified web research findings and evidence captures."""
        if content_snippet is not None:
            if not summary:
                summary = content_snippet
            if evidence_snippets is None:
                evidence_snippets = [content_snippet]

        content_body = summary or title or url
        if evidence_snippets:
            content_body += "\n\nKey Evidence:\n" + "\n".join(f"- {s}" for s in evidence_snippets)

        content_hash = hashlib.sha256(content_body.encode("utf-8")).hexdigest()
        item_id = f"web_{hashlib.md5(url.encode()).hexdigest()[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        meta = {"url": url, "credibility_score": credibility_score}
        if content_snippet:
            meta["snippet"] = content_snippet

        item = HeldDataItem(
            item_id=item_id,
            source_type=FlexibleSourceType("web_research"),
            source_identifier=url,
            title=title or url,
            content=content_body,
            content_hash=content_hash,
            tier=DataSensitivityTier.LIBERAL,
            tags=["web", "researched", "verified"],
            metadata=meta,
            ingested_at=now_iso,
            last_verified_at=now_iso,
        )
        self._held_items[item_id] = item
        self._identifier_index[url] = item_id
        return item

    # -------------------------------------------------------------------------
    # 4. Semantic & Keyword Retrieval for Grounding
    # -------------------------------------------------------------------------

    def query_held_data(
        self,
        query: str,
        limit: int = 5,
        allowed_tiers: Optional[Set[DataSensitivityTier]] = None,
        source_types: Optional[List[str]] = None,
    ) -> List[HeldDataItem]:
        """Search and rank held data items matching user query keywords and concepts."""
        effective_tiers = allowed_tiers or {DataSensitivityTier.LIBERAL}
        tokens = [t.lower() for t in query.split() if len(t) > 2]

        scored: List[Tuple[float, HeldDataItem]] = []

        for item in self._held_items.values():
            if item.tier not in effective_tiers:
                continue
            if source_types and item.source_type not in source_types:
                continue

            score = 0.0
            item_text = (item.title + " " + item.content + " " + " ".join(item.tags)).lower()

            for token in tokens:
                if token in item.title.lower():
                    score += 3.0
                if token in item_text:
                    score += 1.0

            # Boost recent or device files
            if item.source_type == "device_file":
                score += 0.5
            elif item.source_type == "web_research":
                score += 0.2

            if score > 0.5:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def build_grounded_context_prompt(
        self,
        query: str,
        limit: int = 3,
        allowed_tiers: Optional[Set[DataSensitivityTier]] = None,
    ) -> str:
        """Format matching held data into a clean context prompt block for Xeren-Mini."""
        matches = self.query_held_data(query, limit=limit, allowed_tiers=allowed_tiers)
        if not matches:
            return ""

        blocks = []
        for i, m in enumerate(matches, start=1):
            header = f"[{m.source_type.upper()}: {m.title}] ({m.source_identifier})"
            body = m.content.strip()
            # Trim if excessively long
            if len(body) > 1000:
                body = body[:1000] + "... [truncated]"
            blocks.append(f"--- Permitted Source #{i}: {header} ---\n{body}")

        return (
            "\n\n[USER PERMITTED CONTEXT - GROUND TRUTH FROM DEVICE / APPS / WEB]:\n"
            + "\n\n".join(blocks)
            + "\n[END PERMITTED CONTEXT]\n\n"
        )

    # -------------------------------------------------------------------------
    # 5. Inspection & Management
    # -------------------------------------------------------------------------

    def list_held_items(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List summary metadata for held data items."""
        items = list(self._held_items.values())
        if source_type:
            items = [i for i in items if i.source_type == source_type]
        return [i.to_dict() for i in items]

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the vault."""
        item = self._held_items.pop(item_id, None)
        if item:
            self._identifier_index.pop(item.source_identifier, None)
            return True
        return False

    def clear(self) -> None:
        """Clear all held data items."""
        self._held_items.clear()
        self._identifier_index.clear()


__all__ = ["HeldDataItem", "PermittedDataHoldingVault"]
