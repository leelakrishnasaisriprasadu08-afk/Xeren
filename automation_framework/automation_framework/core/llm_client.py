"""
Thin wrapper around the Anthropic API so the rest of the framework never
talks to the SDK directly. Swap this one file to use a different provider
(OpenAI, a local model, whatever) without touching any plugin code.
"""
import os
import json
import asyncio
from typing import Any, Dict, Optional
from xeren.models import create_llm


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # We ignore api_key and model and just use Xeren's default LLM
        # which prioritizes Gemini for complex tasks or Groq.
        self._client = create_llm()

    def available(self) -> bool:
        return self._client is not None

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1500) -> str:
        """Return a plain-text completion. Raises if no API key/SDK is set up
        -- callers should check .available() first if they want to degrade
        gracefully instead."""
        if not self._client:
            raise RuntimeError("LLM client not configured.")
            
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
            # If we are in a running loop, we can't use asyncio.run.
            # But the automation framework main.py is synchronous.
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
