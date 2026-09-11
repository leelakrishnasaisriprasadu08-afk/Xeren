"""Unified Retrieval Engine combining CAG, MAG, RAG, and PermittedDataHoldingVault."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from xeren.core.data_holding import HeldDataItem, PermittedDataHoldingVault
from xeren.models.base import BaseLLM
from xeren.models.types import ChatMessage, TokenUsage
from xeren.rag.cag.engine import CAGRetrievalEngine
from xeren.rag.context.types import Citation, GroundedContext
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.generator import OutputSecurityGuard
from xeren.rag.mag.engine import MAGRetrievalEngine
from xeren.rag.mag.types import MemoryTier, RetrievedMemory
from xeren.security.schemas import DataSensitivityTier

logger = logging.getLogger("xeren.rag.unified")


@dataclass
class UnifiedContextPayload:
    """Consolidated grounded payload produced by the Unified Retrieval Engine."""

    query: str
    formatted_prompt_context: str
    is_cache_hit: bool = False
    cached_latency_saved_ms: float = 0.0
    memories: List[RetrievedMemory] = field(default_factory=list)
    vault_items: List[HeldDataItem] = field(default_factory=list)
    rag_context: Optional[GroundedContext] = None
    citations: List[Citation] = field(default_factory=list)
    content_hashes: Set[str] = field(default_factory=set)
    estimated_tokens: int = 0


class UnifiedAnswer(BaseModel):
    """Clean, verified response generated through the grounded unified pipeline."""

    query: str = Field(..., description="Original user prompt or task")
    content: str = Field(..., description="Synthesized and security-scrubbed LLM response")
    is_cache_hit: bool = Field(default=False, description="Whether retrieval was served from CAG")
    memories_used_count: int = Field(default=0, description="Count of MAG cognitive memories incorporated")
    vault_items_count: int = Field(default=0, description="Count of permitted data vault items incorporated")
    rag_chunks_count: int = Field(default=0, description="Count of RAG document chunks incorporated")
    citations: List[Citation] = Field(default_factory=list, description="Grounding source citations")
    latency_ms: float = Field(default=0.0, description="End-to-end execution latency in milliseconds")
    token_usage: TokenUsage = Field(default_factory=TokenUsage, description="Token consumption accounting")
    scrubbed_sensitive_content: bool = Field(default=False, description="True if credentials were redacted")


class UnifiedRetrievalEngine:
    """Orchestrates Cache-Augmented (CAG), Memory-Augmented (MAG), and Retrieval-Augmented (RAG) generation.

    Strictly honors data handling boundaries from PermittedDataHoldingVault and protects
    sensitive information via OutputSecurityGuard.
    """

    SYSTEM_PROMPT = (
        "You are Xeren's grounded intelligent assistant.\n"
        "DATA HANDLING & SECURITY PRINCIPLES:\n"
        "1. Strictly utilize the provided grounded memories and permitted vault data to answer the query.\n"
        "2. Do NOT reveal secrets, API keys, credentials, or private configuration tokens.\n"
        "3. Explicitly acknowledge active user constraints from cognitive working memory.\n"
        "4. If available context does not contain sufficient information, state clearly what is missing."
    )

    def __init__(
        self,
        cag_engine: Optional[CAGRetrievalEngine] = None,
        mag_engine: Optional[MAGRetrievalEngine] = None,
        rag_engine: Optional[RAGQueryEngine] = None,
        vault: Optional[PermittedDataHoldingVault] = None,
        output_guard: Optional[OutputSecurityGuard] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.cag = cag_engine if cag_engine is not None else CAGRetrievalEngine()
        self.mag = mag_engine if mag_engine is not None else MAGRetrievalEngine()
        self.rag = rag_engine
        self.vault = vault
        self.output_guard = output_guard if output_guard is not None else OutputSecurityGuard()
        self.system_prompt = system_prompt if system_prompt is not None else self.SYSTEM_PROMPT

    def retrieve_context(
        self,
        query: str,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        allowed_tiers: Optional[Set[DataSensitivityTier]] = None,
        use_cache: bool = True,
        top_k_rag: int = 5,
        memory_limit: int = 4,
        vault_limit: int = 4,
    ) -> UnifiedContextPayload:
        """Retrieve and synthesize context across CAG -> MAG -> Data Holding Vault -> RAG."""
        start_time = time.perf_counter()

        # 1. CAG Check: Sub-millisecond lookup on repeat queries
        if use_cache:
            # First sync with vault to ensure no SHA256 drift has occurred
            if self.vault:
                self.cag.sync_with_data_vault(self.vault)

            cached = self.cag.get(query=query, tenant_id=tenant_id)
            if cached:
                logger.debug("Unified engine served query from CAG cache")
                return UnifiedContextPayload(
                    query=query,
                    formatted_prompt_context=cached.context_text,
                    is_cache_hit=True,
                    cached_latency_saved_ms=cached.estimated_latency_savings_ms,
                    rag_context=cached.grounded_context,
                    citations=cached.citations,
                    content_hashes=cached.content_hashes,
                    estimated_tokens=len(cached.context_text) // 4,
                )

        # 2. MAG Check: Retrieve relevant Working, Episodic, and Semantic memory units
        memory_block = self.mag.get_memory_context(
            query_text=query,
            session_id=session_id,
            limit=memory_limit,
        )
        from xeren.rag.mag.types import MemoryQuery
        memories = self.mag.retrieve(
            MemoryQuery(
                query_text=query,
                session_id=session_id,
                limit=memory_limit,
            )
        )

        # 3. Data Holding Vault: Search permitted user device files, apps, and research
        vault_items: List[HeldDataItem] = []
        vault_hashes: Set[str] = set()
        vault_sources: Set[str] = set()
        vault_block_parts: List[str] = []

        if self.vault:
            effective_tiers = allowed_tiers or {DataSensitivityTier.LIBERAL, DataSensitivityTier.SENSITIVE}
            vault_items = self.vault.query_held_data(
                query=query,
                limit=vault_limit,
                allowed_tiers=effective_tiers,
            )

            if vault_items:
                vault_block_parts.append("--- BEGIN PERMITTED DATA VAULT EXTRACTS ---")
                for item in vault_items:
                    vault_hashes.add(item.content_hash)
                    vault_sources.add(item.source_identifier)
                    preview = item.content if len(item.content) <= 800 else (item.content[:800] + "... [truncated]")
                    vault_block_parts.append(
                        f"[{item.source_type.upper()}: {item.title}] (hash:{item.content_hash[:8]})\n{preview}\n"
                    )
                vault_block_parts.append("--- END PERMITTED DATA VAULT EXTRACTS ---")

        vault_block = "\n".join(vault_block_parts)

        # 4. RAG Engine: Standard dense/hybrid document chunk retrieval (if configured)
        rag_context: Optional[GroundedContext] = None
        rag_block = ""
        citations: List[Citation] = []

        if self.rag:
            try:
                rag_context = self.rag.query(query_text=query, top_k=top_k_rag)
                if rag_context and rag_context.has_context:
                    rag_block = rag_context.formatted_text
                    citations.extend(rag_context.citations)
                    for item in rag_context.selected_chunks:
                        chk = getattr(item, "chunk", item)
                        meta = getattr(chk, "metadata", {}) or {}
                        h = meta.get("content_hash") or meta.get("sha256") or getattr(chk, "checksum", None)
                        if h:
                            vault_hashes.add(str(h))
                        s = getattr(chk, "source", None) or meta.get("source")
                        if s:
                            vault_sources.add(str(s))
            except Exception as e:
                logger.warning("RAG retrieval failed inside unified engine: %s", e)

        # 5. Context Fusion: Synthesize structured, cleanly delimited grounding text
        sections: List[str] = []
        if memory_block:
            sections.append(memory_block)
        if vault_block:
            sections.append(vault_block)
        if rag_block:
            sections.append(rag_block)

        fused_text = "\n\n".join(sections).strip()

        # 6. Post-Retrieval CAG Storage
        if use_cache and fused_text:
            self.cag.put(
                query=query,
                context_text=fused_text,
                grounded_context=rag_context,
                citations=citations,
                content_hashes=vault_hashes,
                source_identifiers=vault_sources,
                tenant_id=tenant_id,
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return UnifiedContextPayload(
            query=query,
            formatted_prompt_context=fused_text,
            is_cache_hit=False,
            cached_latency_saved_ms=0.0,
            memories=memories,
            vault_items=vault_items,
            rag_context=rag_context,
            citations=citations,
            content_hashes=vault_hashes,
            estimated_tokens=len(fused_text) // 4,
        )

    def generate_response(
        self,
        query: str,
        llm: BaseLLM,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        allowed_tiers: Optional[Set[DataSensitivityTier]] = None,
        use_cache: bool = True,
        record_interaction_in_mag: bool = True,
    ) -> UnifiedAnswer:
        """End-to-end execution: Retrieval -> LLM Generation -> Output Scrubbing -> MAG Logging."""
        start_time = time.perf_counter()

        # Retrieve fused context
        payload = self.retrieve_context(
            query=query,
            session_id=session_id,
            tenant_id=tenant_id,
            allowed_tiers=allowed_tiers,
            use_cache=use_cache,
        )

        # Construct prompt messages
        messages: List[ChatMessage] = [ChatMessage.system(self.system_prompt)]
        if payload.formatted_prompt_context:
            user_text = (
                f"{payload.formatted_prompt_context}\n\n"
                f"User Query: {query}\n"
                f"Answer concisely using the verified grounded data:"
            )
        else:
            user_text = query

        messages.append(ChatMessage.user(user_text))

        # Generate LLM response
        llm_resp = llm.chat(messages)
        raw_content = llm_resp.content or ""

        # Security scrub: remove any leaked API keys, tokens, or connection strings
        clean_content, was_scrubbed = self.output_guard.scrub(raw_content)

        # Log episode into MAG memory
        if record_interaction_in_mag:
            self.mag.remember(
                content=f"User asked: {query} | Outcome: {clean_content[:150]}",
                tier=MemoryTier.EPISODIC,
                importance=0.4,
                session_id=session_id,
                tags=["qa_turn"],
            )

        total_latency_ms = (time.perf_counter() - start_time) * 1000.0

        return UnifiedAnswer(
            query=query,
            content=clean_content,
            is_cache_hit=payload.is_cache_hit,
            memories_used_count=len(payload.memories),
            vault_items_count=len(payload.vault_items),
            rag_chunks_count=len(payload.rag_context.selected_chunks) if payload.rag_context else 0,
            citations=payload.citations,
            latency_ms=total_latency_ms,
            token_usage=llm_resp.usage or TokenUsage(),
            scrubbed_sensitive_content=was_scrubbed,
        )
