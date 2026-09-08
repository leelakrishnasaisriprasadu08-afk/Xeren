"""Configuration class for Xeren custom LLM architecture.

Two-Stage Training System:
  Stage 1 - Xeren-Mini-50  (~70M params, vocab=16K, 8 layers): Language + basic plugin grounding
  Stage 2 - Xeren-Mini-150 (~120M params, vocab=32K, 18 layers): Full domain specialization
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class XerenConfig:
    vocab_size: int = 16384
    dim: int = 512
    n_layers: int = 8
    n_heads: int = 8
    n_kv_heads: Optional[int] = 4  # GQA (Grouped Query Attention)
    hidden_dim: Optional[int] = None  # SwiGLU intermediate dim
    max_seq_len: int = 1024
    norm_eps: float = 1e-6
    rope_theta: float = 10000.0
    dropout: float = 0.0
    tie_word_embeddings: bool = True

    # Domain specialization heads (enabled in Stage 2)
    num_plugins: int = 9          # research, coding, file, browser, api, conversation, data, knowledge, website
    enable_plugin_head: bool = False
    enable_confidence_head: bool = False
    enable_threat_head: bool = False
    num_threat_classes: int = 6   # clean, malware, shellcode, phishing, exploit, suspicious

    def __post_init__(self):
        if self.n_kv_heads is None:
            self.n_kv_heads = self.n_heads
        if self.hidden_dim is None:
            # Standard SwiGLU formula: ~ 8/3 * dim rounded to multiple of 64
            hidden_dim = int(2 * (4 * self.dim) / 3)
            self.hidden_dim = ((hidden_dim + 63) // 64) * 64

    # -------------------------------------------------------------------------
    # Nano — CPU verification (~12M params)
    # -------------------------------------------------------------------------
    @classmethod
    def nano(cls, vocab_size: int = 16384) -> "XerenConfig":
        """Xeren-Nano preset (~12M params) optimized for fast CPU verification."""
        return cls(
            vocab_size=vocab_size,
            dim=256,
            n_layers=4,
            n_heads=4,
            n_kv_heads=2,
            max_seq_len=512,
            norm_eps=1e-5,
            tie_word_embeddings=True,
        )

    # -------------------------------------------------------------------------
    # Stage 1 — Xeren-Mini-50 (~70M params, vocab=16K)
    # Foundation: language, basic planning, plugin call grounding
    # VRAM: ~4.5GB on RTX A1000, Training time: ~30-50 min
    # -------------------------------------------------------------------------
    @classmethod
    def stage1(cls, vocab_size: int = 16384) -> "XerenConfig":
        """Xeren-Mini-50: Stage 1 foundation model (~70M params).

        Trains from scratch on:
        - General instruction following (Dolly, xLAM)
        - Multi-hop reasoning (HotpotQA)
        - Agentic task trajectories (AgentInstruct, local Xeren data)
        - Basic plugin dispatch learning
        """
        return cls(
            vocab_size=vocab_size,
            dim=768,
            n_layers=12,
            n_heads=12,
            n_kv_heads=4,
            hidden_dim=2048,
            max_seq_len=1024,
            norm_eps=1e-6,
            rope_theta=10000.0,
            dropout=0.1,
            tie_word_embeddings=False,
            num_plugins=9,
            enable_plugin_head=False,
            enable_confidence_head=False,
            enable_threat_head=False,
        )

    # -------------------------------------------------------------------------
    # Stage 2 — Xeren-Mini-150 (~120M params, vocab=32K)
    # Specialization: plugin dispatch, security, confidence, continuous learning
    # VRAM: ~7.2GB on RTX A1000, Training time: ~90-120 min
    # Initialized from Stage 1 checkpoint weights (compatible layers transferred)
    # -------------------------------------------------------------------------
    @classmethod
    def stage2(cls, vocab_size: int = 32768) -> "XerenConfig":
        """Xeren-Mini-150: Stage 2 specialization model (~120M params).

        Fine-tuned from Stage 1 on domain-specific datasets:
        - Plugin architecture & dispatch (Hermes function calling)
        - Workflow planning (AgentInstruct extended)
        - Output prediction with probabilities (OpenR1-Math CoT)
        - Malware & security detection (WildGuard, MMLU security)
        - Continuous learning from user queries via Supabase buffer
        
        New capabilities vs Stage 1:
        - PluginClassificationHead: predicts which plugin to invoke
        - ConfidenceScoreHead: outputs calibrated probability [0.0-1.0]
        - ThreatClassificationHead: malware/security classifier
        """
        return cls(
            vocab_size=vocab_size,
            dim=1024,
            n_layers=18,
            n_heads=16,
            n_kv_heads=4,
            hidden_dim=2816,
            max_seq_len=2048,
            norm_eps=1e-6,
            rope_theta=500000.0,  # Extended RoPE for longer context
            dropout=0.05,
            tie_word_embeddings=False,
            num_plugins=9,
            enable_plugin_head=True,
            enable_confidence_head=True,
            enable_threat_head=True,
            num_threat_classes=6,
        )

    # Backward-compatible alias
    @classmethod
    def mini(cls, vocab_size: int = 32768) -> "XerenConfig":
        """Alias for stage2 — backward compatibility."""
        return cls.stage2(vocab_size=vocab_size)

    def parameter_estimate(self) -> int:
        """Rough estimate of total model parameters."""
        embed = self.vocab_size * self.dim
        attn = self.n_layers * (
            self.dim * self.n_heads * (self.dim // self.n_heads) +  # wq
            self.dim * self.n_kv_heads * (self.dim // self.n_heads) * 2 +  # wk, wv
            self.dim * self.dim  # wo
        )
        ffn = self.n_layers * (self.dim * self.hidden_dim * 3)
        norm = self.n_layers * self.dim * 2 + self.dim
        lm_head = 0 if self.tie_word_embeddings else self.vocab_size * self.dim
        return embed + attn + ffn + norm + lm_head
