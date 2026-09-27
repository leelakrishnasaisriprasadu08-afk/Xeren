"""Cache-Augmented Generation (CAG) retrieval engine for Xeren."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import logging
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from xeren.rag.cag.types import CachedContextEntry, CachePolicy, CacheStats
from xeren.rag.context.types import Citation, GroundedContext

logger = logging.getLogger("xeren.rag.cag")


class CAGRetrievalEngine:
    """High-performance Cache-Augmented Generation engine.

    Provides sub-millisecond grounded context retrieval for repeated or overlapping queries,
    with automatic cryptographic SHA256 invalidation when underlying vault data changes.
    """

    def __init__(
        self,
        default_ttl_seconds: float = 3600.0,
        max_entries: int = 1000,
        policy: CachePolicy = CachePolicy.ADAPTIVE,
        time_provider: Optional[Callable[[], float]] = None,
    ) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self.max_entries = max_entries
        self.policy = policy
        self._time = time_provider or time.time

        # In-memory storage ordered by access recency (LRU)
        self._entries: OrderedDict[str, CachedContextEntry] = OrderedDict()

        # Inverted index: content_hash -> set of cache_keys
        self._hash_to_keys: Dict[str, Set[str]] = {}

        # Inverted index: source_identifier -> set of cache_keys
        self._source_to_keys: Dict[str, Set[str]] = {}

        # Inverted index: tenant_id -> set of cache_keys
        self._tenant_to_keys: Dict[str, Set[str]] = {}

        # Metrics accounting
        self._stats = CacheStats()

    @property
    def stats(self) -> CacheStats:
        """Return operational telemetry for cache hits, misses, and invalidations."""
        return self._stats

    def compute_cache_key(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> str:
        """Compute a canonical cache key from normalized query text and context boundary."""
        # Normalize whitespace and case for stable query hashing
        cleaned = re.sub(r"\s+", " ", query.strip().lower())
        tenant_part = (tenant_id or "global").strip().lower()
        scope_part = (scope or "default").strip().lower()
        raw = f"{tenant_part}::{scope_part}::{cleaned}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> Optional[CachedContextEntry]:
        """Lookup cached context. Returns entry on hit, None on miss or expiration."""
        key = self.compute_cache_key(query=query, tenant_id=tenant_id, scope=scope)
        entry = self._entries.get(key)

        now = self._time()

        if entry is None:
            self._stats.misses += 1
            return None

        # Check TTL expiration
        if entry.is_expired(now):
            logger.debug("CAG cache entry %s expired (TTL surpassed)", key)
            self._remove_entry(key)
            self._stats.evictions += 1
            self._stats.misses += 1
            return None

        # Cache Hit: touch entry, move to end of OrderedDict (most recently used)
        entry.touch(now)
        self._entries.move_to_end(key)
        self._stats.hits += 1
        self._stats.total_latency_saved_ms += entry.estimated_latency_savings_ms
        if entry.grounded_context:
            self._stats.total_tokens_saved += entry.grounded_context.estimated_tokens

        logger.debug("CAG cache hit for query key: %s (hit_rate: %.2f)", key, self._stats.hit_rate)
        return entry

    def put(
        self,
        query: str,
        context_text: str,
        grounded_context: Optional[GroundedContext] = None,
        citations: Optional[List[Citation]] = None,
        content_hashes: Optional[Iterable[str]] = None,
        source_identifiers: Optional[Iterable[str]] = None,
        tenant_id: Optional[str] = None,
        scope: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
        estimated_latency_savings_ms: float = 85.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CachedContextEntry:
        """Store or update a grounded context payload in the CAG cache."""
        key = self.compute_cache_key(query=query, tenant_id=tenant_id, scope=scope)
        now = self._time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = (now + ttl) if ttl > 0 else None

        # Clean old inverted indices if key already exists
        if key in self._entries:
            self._remove_entry(key)

        # Evict least recently used if at maximum capacity
        while len(self._entries) >= self.max_entries and self._entries:
            oldest_key, _ = self._entries.popitem(last=False)
            self._stats.evictions += 1
            logger.debug("Evicted oldest LRU cache entry %s", oldest_key)

        entry_hashes = set(content_hashes or [])
        entry_sources = set(source_identifiers or [])

        # Automatically extract hashes and sources from GroundedContext if available
        if grounded_context:
            for item in grounded_context.selected_chunks:
                chk = getattr(item, "chunk", item)
                meta = getattr(chk, "metadata", {}) or {}
                h = meta.get("content_hash") or meta.get("sha256") or getattr(chk, "checksum", None)
                if h:
                    entry_hashes.add(str(h))
                s = getattr(chk, "source", None) or meta.get("source")
                if s:
                    entry_sources.add(str(s))

        entry = CachedContextEntry(
            cache_key=key,
            query=query,
            context_text=context_text,
            grounded_context=grounded_context,
            citations=citations or (grounded_context.citations if grounded_context else []),
            content_hashes=entry_hashes,
            source_identifiers=entry_sources,
            tenant_id=tenant_id,
            scope=scope,
            created_at=now,
            expires_at=expires_at,
            last_accessed_at=now,
            access_count=1,
            estimated_latency_savings_ms=estimated_latency_savings_ms,
            metadata=metadata or {},
        )

        self._entries[key] = entry

        # Update inverted indexes
        for h in entry_hashes:
            self._hash_to_keys.setdefault(h, set()).add(key)
        for s in entry_sources:
            self._source_to_keys.setdefault(s, set()).add(key)
        if tenant_id:
            self._tenant_to_keys.setdefault(tenant_id, set()).add(key)

        return entry

    def invalidate_by_hash(self, content_hash: str) -> int:
        """Invalidate all cached entries dependent on a specific document SHA256 content hash."""
        keys = self._hash_to_keys.get(content_hash, set()).copy()
        count = 0
        for key in keys:
            if self._remove_entry(key):
                count += 1
        self._stats.invalidations += count
        if count > 0:
            logger.info("CAG invalidated %d cached entries for hash %s", count, content_hash)
        return count

    def invalidate_by_source(self, source_identifier: str) -> int:
        """Invalidate all cached entries linked to a given file path or URI."""
        keys = self._source_to_keys.get(source_identifier, set()).copy()
        count = 0
        for key in keys:
            if self._remove_entry(key):
                count += 1
        self._stats.invalidations += count
        if count > 0:
            logger.info("CAG invalidated %d cached entries for source %s", count, source_identifier)
        return count

    def invalidate_by_tenant(self, tenant_id: str) -> int:
        """Invalidate all cached entries belonging to a tenant."""
        keys = self._tenant_to_keys.get(tenant_id, set()).copy()
        count = 0
        for key in keys:
            if self._remove_entry(key):
                count += 1
        self._stats.invalidations += count
        return count

    def sync_with_data_vault(self, vault: Any) -> int:
        """Synchronize with PermittedDataHoldingVault.

        Checks all held items in the vault and invalidates any cache entry where
        the source content hash has drifted from the cached hash.
        """
        invalidated_total = 0
        held_items = getattr(vault, "_held_items", {})
        if not held_items:
            return 0

        # Build current source -> hash mapping from the vault
        current_source_hashes: Dict[str, str] = {}
        for item in held_items.values():
            if hasattr(item, "source_identifier") and hasattr(item, "content_hash"):
                current_source_hashes[str(item.source_identifier)] = str(item.content_hash)

        # Check each entry
        keys_to_purge: Set[str] = set()
        for key, entry in self._entries.items():
            for src in entry.source_identifiers:
                if src in current_source_hashes:
                    current_hash = current_source_hashes[src]
                    # If this entry doesn't contain current hash, it's stale
                    if entry.content_hashes and current_hash not in entry.content_hashes:
                        keys_to_purge.add(key)
                        break

        for key in keys_to_purge:
            if self._remove_entry(key):
                invalidated_total += 1

        self._stats.invalidations += invalidated_total
        if invalidated_total > 0:
            logger.info("CAG synced with Data Holding Vault: purged %d stale entries", invalidated_total)
        return invalidated_total

    def prewarm(self, entries: List[Dict[str, Any]]) -> int:
        """Pre-warm cache with common queries and known grounded contexts."""
        count = 0
        for data in entries:
            q = data.get("query")
            txt = data.get("context_text")
            if q and txt:
                self.put(
                    query=q,
                    context_text=txt,
                    grounded_context=data.get("grounded_context"),
                    citations=data.get("citations"),
                    content_hashes=data.get("content_hashes"),
                    source_identifiers=data.get("source_identifiers"),
                    tenant_id=data.get("tenant_id"),
                    scope=data.get("scope"),
                    ttl_seconds=data.get("ttl_seconds"),
                )
                count += 1
        return count

    def clear(self) -> None:
        """Completely flush the cache and all inverted indices."""
        self._entries.clear()
        self._hash_to_keys.clear()
        self._source_to_keys.clear()
        self._tenant_to_keys.clear()

    def _remove_entry(self, key: str) -> bool:
        """Internal helper to remove an entry and its index pointers."""
        entry = self._entries.pop(key, None)
        if not entry:
            return False

        # Clean hash index
        for h in entry.content_hashes:
            if h in self._hash_to_keys:
                self._hash_to_keys[h].discard(key)
                if not self._hash_to_keys[h]:
                    del self._hash_to_keys[h]

        # Clean source index
        for s in entry.source_identifiers:
            if s in self._source_to_keys:
                self._source_to_keys[s].discard(key)
                if not self._source_to_keys[s]:
                    del self._source_to_keys[s]

        # Clean tenant index
        if entry.tenant_id and entry.tenant_id in self._tenant_to_keys:
            self._tenant_to_keys[entry.tenant_id].discard(key)
            if not self._tenant_to_keys[entry.tenant_id]:
                del self._tenant_to_keys[entry.tenant_id]

        return True

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return True
