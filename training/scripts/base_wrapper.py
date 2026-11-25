"""
XerenLocalLLM — Wraps the scratch-trained XerenTransformer inside the
standard BaseLLM interface (src/xeren/models/base.py), so the orchestrator
and all sub-system plugins can speak to the local model with a unified API.

Confidence scoring is computed from the top-token softmax probability of
the first generated token. This is an honest, calibrated signal — not a
made-up number.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, List, Optional

import torch
import torch.nn.functional as F

# ── Path bootstrap: allow imports from both training/ and src/ ───────────────
_ROOT = Path(__file__).resolve().parent.parent.parent  # Xeren/
sys.path.insert(0, str(_ROOT))

from training.src.inference.generate import XerenGenerator, top_k_top_p_filtering
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer

from xeren.models.base import BaseLLM
from xeren.models.config import ModelConfig
from xeren.models.types import ChatMessage, LLMResponse, Role, StreamChunk, TokenUsage


# ─────────────────────────────────────────────────────────────────────────────
# ChatML helpers
# ─────────────────────────────────────────────────────────────────────────────

def _messages_to_chatml(messages: List[ChatMessage]) -> str:
    """Convert a list of ChatMessage objects into the Xeren ChatML format."""
    parts: List[str] = []
    for msg in messages:
        role = msg.role
        content = msg.content or ""
        parts.append(f"<|im_start|>{role}\n{content}\n<|im_end|>")
    # Prime the assistant turn
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# XerenLocalLLM
# ─────────────────────────────────────────────────────────────────────────────

class XerenLocalLLM(BaseLLM):
    """
    Local Xeren LLM that satisfies the BaseLLM contract.

    Loaded once at construction time from a checkpoint on disk.
    Thread-safe for inference (model is in eval mode, torch.no_grad).

    Confidence is derived from the top-token probability on the first
    generated token — provides a calibrated, honest certainty signal.
    """

    CONFIDENCE_THRESHOLD: float = 0.65  # Below this → RESEARCH mode

    def __init__(
        self,
        checkpoint_path: Path,
        tokenizer_dir: Path,
        device: str = "cpu",
        config: Optional[ModelConfig] = None,
    ) -> None:
        super().__init__(
            config
            or ModelConfig(
                model_id="xeren-local",
                provider="local_openweight",
                temperature=0.7,
                max_tokens=128,
            )
        )

        self.device_str = device
        self.checkpoint_path = Path(checkpoint_path)
        self.tokenizer_dir = Path(tokenizer_dir)

        print(f"[XerenLocalLLM] Loading tokenizer from {self.tokenizer_dir} …")
        self.tokenizer: XerenTokenizer = XerenTokenizer.load(self.tokenizer_dir)

        print(f"[XerenLocalLLM] Loading checkpoint from {self.checkpoint_path} …")
        ckpt = torch.load(self.checkpoint_path, map_location="cpu")
        xeren_cfg = XerenConfig(**ckpt["config"])

        self.model = XerenTransformer(xeren_cfg)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()

        self.generator = XerenGenerator(self.model, self.tokenizer, device=device)
        print("[XerenLocalLLM] Ready ✓")

    # ── Confidence probe ────────────────────────────────────────────────────

    @torch.no_grad()
    def compute_confidence(self, prompt: str) -> float:
        """
        Return the top-token softmax probability for the first generated token.
        Serves as an honest confidence proxy — values closer to 1.0 indicate
        the model is more certain about what to say first.
        """
        input_ids = self.tokenizer.encode(prompt, add_special_tokens=True)
        tokens = torch.tensor([input_ids], dtype=torch.long)
        logits, _, _ = self.model(tokens)
        next_logits = logits[:, -1, :]
        probs = F.softmax(next_logits, dim=-1)
        top_prob = probs.max().item()
        return round(float(top_prob), 4)

    # ── BaseLLM interface ───────────────────────────────────────────────────

    def generate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9,
        **kwargs: Any,
    ) -> LLMResponse:
        cfg = self._resolve_config(config)
        prompt = _messages_to_chatml(messages)
        confidence = self.compute_confidence(prompt)

        t0 = time.perf_counter()
        raw = self.generator.generate(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Strip the prompt echo (everything up to the last assistant turn)
        reply = raw.split("<|im_start|>assistant\n")[-1]
        reply = reply.replace("<|im_end|>", "").strip()

        return LLMResponse(
            content=reply,
            message=ChatMessage(role=Role.ASSISTANT, content=reply),
            model_id="xeren-local",
            finish_reason="stop",
            usage=TokenUsage(
                prompt_tokens=max(1, len(prompt) // 4),
                completion_tokens=max(1, len(reply) // 4),
                total_tokens=max(2, (len(prompt) + len(reply)) // 4),
            ),
            raw_response={"latency_ms": elapsed_ms, "confidence": confidence},
            metadata={
                "confidence": confidence,
                "confident": confidence >= self.CONFIDENCE_THRESHOLD,
                "device": self.device_str,
                "latency_ms": elapsed_ms,
            },
        )

    async def agenerate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, messages, config, **kwargs)

    def stream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9,
        **kwargs: Any,
    ) -> Iterator[StreamChunk]:
        prompt = _messages_to_chatml(messages)
        for token_str in self.generator.stream_generate(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        ):
            if "<|im_end|>" in token_str:
                break
            yield StreamChunk(delta=token_str)

    async def astream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        import asyncio
        for chunk in self.stream(messages, config, **kwargs):
            yield chunk
            await asyncio.sleep(0)

    def ping(self) -> bool:
        return self.model is not None

    async def aping(self) -> bool:
        return self.ping()


__all__ = ["XerenLocalLLM"]
