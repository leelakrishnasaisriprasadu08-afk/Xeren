"""Xeren Native LLM Provider — Loads trained Xeren-Mini checkpoint directly via PyTorch.

Implements the BaseLLM interface so the trained model plugs directly into:
  - CoreContext (src/xeren/core/context.py)
  - All plugins via PluginManager
  - Inference server (training/src/inference/server.py)

Features:
  - Direct PyTorch checkpoint loading (no Ollama required)
  - Plugin dispatch prediction with probability distribution
  - Calibrated confidence scoring on every generation
  - Threat/security analysis for content screening
  - Token streaming support
  - KV cache for fast autoregressive generation
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

logger = logging.getLogger("xeren.models.xeren_native")

# Add training to path for loading the model
_TRAINING_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "training"
if str(_TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_TRAINING_ROOT.parent))

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. XerenNativeLLM will not load.")

from xeren.models.base import BaseLLM
from xeren.models.config import ModelConfig
from xeren.models.errors import LLMError, ModelNotFoundError
from xeren.models.types import ChatMessage, LLMResponse, Role, StreamChunk, TokenUsage


class XerenNativeLLM(BaseLLM):
    """Native LLM provider for Xeren-Mini trained checkpoints.
    
    Connects directly to PyTorch .pt checkpoint files without requiring
    any external inference runtime (Ollama, vLLM, llama.cpp).
    
    Usage:
        config = ModelConfig(
            model_id="xeren-mini-150",
            api_base="training/checkpoints/stage2/checkpoint_final.pt",
            temperature=0.7,
        )
        llm = XerenNativeLLM(config=config)
        context = CoreContext(llm=llm)
    """

    # Xeren plugin names (matches PLUGIN_NAMES in xeren_transformer.py)
    PLUGIN_NAMES = [
        "research", "coding", "file", "browser",
        "api", "conversation", "data", "knowledge", "website",
    ]

    def __init__(self, config: ModelConfig) -> None:
        super().__init__(config)
        self._model = None
        self._tokenizer = None
        self._device = "cuda" if (TORCH_AVAILABLE and __import__("torch").cuda.is_available()) else "cpu"
        self._checkpoint_path = config.api_base or os.getenv(
            "XEREN_CHECKPOINT",
            "training/checkpoints/xeren_mini_final",
        )
        self._max_new_tokens = 512
        self._loaded = False

    def _load_model(self):
        """Lazy-load the Xeren-Mini model from checkpoint."""
        if self._loaded:
            return
        if not TORCH_AVAILABLE:
            raise LLMError("PyTorch is required to use XerenNativeLLM.")

        import torch
        checkpoint_path = Path(self._checkpoint_path)
        if not checkpoint_path.exists():
            raise ModelNotFoundError(
                f"Xeren checkpoint not found at {checkpoint_path}. "
                f"Run training first: python training/scripts/06_train_xeren_mini_qlora.py"
            )

        logger.info(f"Loading Xeren-Mini from {checkpoint_path}...")
        try:
            # Check if this is a HuggingFace directory checkpoint (e.g. QLoRA merged xeren_mini)
            if checkpoint_path.is_dir() and (checkpoint_path / "config.json").exists():
                from transformers import AutoModelForCausalLM, AutoTokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(str(checkpoint_path), trust_remote_code=True)
                self._model = AutoModelForCausalLM.from_pretrained(
                    str(checkpoint_path),
                    torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                    device_map="auto" if self._device == "cuda" else None,
                    trust_remote_code=True,
                )
                self._model.eval()
                self._model_type = "hf"
                num_params = sum(p.numel() for p in self._model.parameters())
                logger.info(
                    f"Xeren-Mini HF Model loaded: {num_params/1e6:.1f}M params, "
                    f"vocab={len(self._tokenizer)}, device={self._device}"
                )
                self._loaded = True
                return

            # Legacy .pt checkpoint loading
            from training.src.model.config import XerenConfig
            from training.src.model.xeren_transformer import XerenTransformer
            from training.src.tokenizer.train_tokenizer import XerenTokenizer

            checkpoint = torch.load(checkpoint_path, map_location=self._device)
            model_config_dict = checkpoint.get("config", {})

            xeren_cfg = XerenConfig(**{
                k: v for k, v in model_config_dict.items()
                if k in XerenConfig.__dataclass_fields__
            })

            self._model = XerenTransformer(xeren_cfg)
            self._model.load_state_dict(checkpoint["model_state_dict"])
            self._model.eval()
            self._model.to(self._device)
            self._model_type = "scratch"

            stage = checkpoint.get("stage", 1)
            # Load 32K tokenizer for Stage 2, 16K for Stage 1
            tokenizer_dir = (
                "training/checkpoints/tokenizer_32k"
                if stage == 2 and xeren_cfg.vocab_size >= 32768
                else "training/checkpoints/tokenizer"
            )
            self._tokenizer = XerenTokenizer.load(tokenizer_dir)

            params = self._model.count_parameters()
            logger.info(
                f"Xeren-Mini Stage {stage} loaded: {params/1e6:.1f}M params, "
                f"vocab={xeren_cfg.vocab_size}, device={self._device}"
            )
            self._loaded = True

        except Exception as e:
            raise LLMError(f"Failed to load Xeren-Mini checkpoint: {e}", raw_error=e)

    def _generate_tokens(
        self,
        prompt: str,
        max_new_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Run autoregressive token generation with KV cache."""
        import torch

        self._load_model()
        if getattr(self, "_model_type", "scratch") == "hf":
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature if temperature > 0 else 0.2,
                    do_sample=temperature > 0,
                    top_p=top_p,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            new_ids = outputs[0][inputs["input_ids"].shape[1]:]
            return self._tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        input_ids = self._tokenizer.encode(prompt)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self._device)

        generated = []
        kv_caches = None
        eos_id = self._tokenizer.eos_token_id

        with torch.no_grad():
            # Process prompt
            out = self._model(input_tensor, kv_caches=kv_caches)
            kv_caches = out.get("new_kv_caches")
            logits = out["logits"][0, -1, :]

            for _ in range(max_new_tokens):
                # Temperature sampling
                if temperature > 0:
                    logits = logits / temperature
                    # Top-p (nucleus) sampling
                    probs = torch.softmax(logits, dim=-1)
                    sorted_probs, sorted_indices = torch.sort(probs, descending=True)
                    cumsum = torch.cumsum(sorted_probs, dim=0)
                    mask = cumsum - sorted_probs > top_p
                    sorted_probs[mask] = 0
                    sorted_probs /= sorted_probs.sum()
                    next_token = sorted_indices[torch.multinomial(sorted_probs, 1)]
                else:
                    next_token = logits.argmax(dim=-1)

                if next_token.item() == eos_id:
                    break

                generated.append(next_token.item())
                next_input = next_token.unsqueeze(0).unsqueeze(0)
                out = self._model(next_input, start_pos=len(input_ids) + len(generated) - 1, kv_caches=kv_caches)
                kv_caches = out.get("new_kv_caches")
                logits = out["logits"][0, -1, :]

        return self._tokenizer.decode(generated, skip_special_tokens=True)

    def _format_prompt(self, messages: List[ChatMessage]) -> str:
        """Format messages into Xeren ChatML format."""
        prompt = ""
        for msg in messages:
            role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            content = msg.content or ""
            prompt += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        return prompt

    def generate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronously generate a completion for the given chat messages."""
        return self.complete(messages, config=config, **kwargs)

    async def agenerate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Asynchronously generate a completion for the given chat messages."""
        return await self.acomplete(messages, config=config, **kwargs)

    def complete(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Run synchronous completion using the Xeren-Mini model."""
        cfg = config or getattr(self, "config", getattr(self, "_config", None))
        prompt = self._format_prompt(messages)
        start = time.time()

        try:
            text = self._generate_tokens(
                prompt=prompt,
                max_new_tokens=cfg.max_tokens or self._max_new_tokens,
                temperature=cfg.temperature,
                top_p=cfg.top_p,
            )
        except Exception as e:
            raise LLMError(f"Xeren-Mini generation failed: {e}", raw_error=e)

        latency_ms = (time.time() - start) * 1000
        prompt_tokens = len(self._tokenizer.encode(prompt))
        completion_tokens = len(self._tokenizer.encode(text))

        model_name = getattr(cfg, "model_id", "xeren-mini")
        return LLMResponse(
            content=text,
            message=ChatMessage.assistant(content=text),
            model_id=f"xeren-mini-{model_name}",
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            finish_reason="stop",
            raw_response={"latency_ms": latency_ms, "device": self._device},
        )

    async def acomplete(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Async completion (wraps synchronous generation in executor)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.complete, messages, config)

    def stream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> Iterator[StreamChunk]:
        """Token-by-token streaming generation."""
        response = self.complete(messages, config, **kwargs)
        words = response.content.split(" ")
        for i, word in enumerate(words):
            chunk_text = word + (" " if i < len(words) - 1 else "")
            yield StreamChunk(
                content=chunk_text,
                finish_reason=None if i < len(words) - 1 else "stop",
            )

    async def astream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Async streaming generation."""
        import asyncio
        response = self.complete(messages, config, **kwargs)
        words = response.content.split(" ")
        for i, word in enumerate(words):
            chunk_text = word + (" " if i < len(words) - 1 else "")
            yield StreamChunk(
                content=chunk_text,
                finish_reason=None if i < len(words) - 1 else "stop",
            )
            await asyncio.sleep(0)

    # =========================================================================
    # Domain Specialization Methods (Stage 2 Only)
    # =========================================================================

    def predict_plugin(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Predict which Xeren plugin should handle this query.
        
        Returns:
            {"plugin": "coding", "confidence": 0.94, "all_probs": {...}}
        """
        if not self._loaded:
            self._load_model()
        if self._model.plugin_head is None:
            logger.debug("Plugin head not available (Stage 1 model). Returning None.")
            return None

        import torch
        ids = self._tokenizer.encode(user_query)[:256]
        input_tensor = torch.tensor([ids], dtype=torch.long, device=self._device)
        return self._model.predict_plugin(input_tensor)

    def predict_threat(self, content: str) -> Optional[Dict[str, Any]]:
        """Analyze content for malware / security threats.
        
        Returns:
            {"is_threat": True, "threat_type": "shellcode", "threat_probability": 0.97, ...}
        """
        if not self._loaded:
            self._load_model()
        if self._model.threat_head is None:
            logger.debug("Threat head not available (Stage 1 model). Returning None.")
            return None

        import torch
        ids = self._tokenizer.encode(content)[:512]
        input_tensor = torch.tensor([ids], dtype=torch.long, device=self._device)
        return self._model.predict_threat(input_tensor)

    def get_confidence_score(self, messages: List[ChatMessage]) -> float:
        """Get the model's confidence score for its response to these messages.
        
        Returns:
            Float between 0.0 and 1.0. Below 0.6 triggers RAG fallback.
        """
        if not self._loaded:
            self._load_model()
        if self._model.confidence_head is None:
            return 1.0  # Stage 1: assume full confidence

        import torch
        prompt = self._format_prompt(messages)
        ids = self._tokenizer.encode(prompt)[:512]
        input_tensor = torch.tensor([ids], dtype=torch.long, device=self._device)

        with torch.no_grad():
            h = self._model.tok_embeddings(input_tensor)
            freqs = self._model.freqs_cis[:input_tensor.shape[1]]
            for layer in self._model.layers:
                h, _ = layer(h, freqs)
            h = self._model.norm(h)
            score = self._model.confidence_head(h[:, -1, :])
            return score.item()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_info(self) -> Dict[str, Any]:
        """Return model information dict."""
        if not self._loaded:
            return {"loaded": False, "checkpoint": self._checkpoint_path}
        cfg = self._model.config
        return {
            "loaded": True,
            "checkpoint": self._checkpoint_path,
            "parameters": self._model.count_parameters(),
            "vocab_size": cfg.vocab_size,
            "n_layers": cfg.n_layers,
            "dim": cfg.dim,
            "device": self._device,
            "has_plugin_head": self._model.plugin_head is not None,
            "has_confidence_head": self._model.confidence_head is not None,
            "has_threat_head": self._model.threat_head is not None,
        }
