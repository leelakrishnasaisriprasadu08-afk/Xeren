"""
Native Xeren LLM and Unified Retrieval Engine (CAG + MAG + RAG) Client.
Operates completely locally and standalone without third-party cloud APIs.
"""
import os
import json
import asyncio
from typing import Any, Dict, Optional
from xeren.models import create_llm
from xeren.rag.unified_engine import UnifiedRetrievalEngine


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, use_rag: bool = True):
        # Prioritize sovereign Xeren native checkpoint
        self._client = create_llm(provider="xeren_native" if os.getenv("XEREN_CHECKPOINT") or os.path.exists("training/checkpoints/xeren_mini_final") else None)
        self._use_rag = use_rag
        self._rag_engine = UnifiedRetrievalEngine() if use_rag else None

    def available(self) -> bool:
        return self._client is not None

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1500) -> str:
        """Return a plain-text completion grounded by the CAG/MAG/RAG pipeline."""
        if not self._client:
            raise RuntimeError("Xeren LLM client not configured or local checkpoint missing.")

        # Grounding with Unified RAG engine when available
        if self._rag_engine and self._use_rag:
            try:
                answer = self._rag_engine.generate_response(
                    query=prompt,
                    llm=self._client,
                    use_cache=True,
                )
                if answer and answer.content:
                    return answer.content
            except Exception:
                # Graceful fallback to direct generation if RAG context fails
                pass
            
        from xeren.models.types import ChatMessage
        messages = []
        if system:
            messages.append(ChatMessage.system(system))
        messages.append(ChatMessage.user(prompt))
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            pass
            
        response = asyncio.run(self._client.agenerate(messages))
        return response.content

    def complete_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        """Ask the model for JSON only, and parse it. Returns {} on
        malformed output rather than crashing the whole pipeline."""
        raw = self.complete(
            prompt,
            system=(system or "") + "\nRespond with ONLY valid JSON. No prose, no markdown fences.",
        )
        cleaned = raw.strip().strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}
