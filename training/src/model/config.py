"""Configuration class for Xeren custom LLM architecture."""

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

    def __post_init__(self):
        if self.n_kv_heads is None:
            self.n_kv_heads = self.n_heads
        if self.hidden_dim is None:
            # Standard SwiGLU formula: ~ 8/3 * dim rounded to multiple of 64
            hidden_dim = int(2 * (4 * self.dim) / 3)
            self.hidden_dim = ((hidden_dim + 63) // 64) * 64

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

    @classmethod
    def mini(cls, vocab_size: int = 32768) -> "XerenConfig":
        """Xeren-Mini preset (~90M params) optimized for single College GPU training from scratch."""
        return cls(
            vocab_size=vocab_size,
            dim=768,
            n_layers=12,
            n_heads=12,
            n_kv_heads=4,
            max_seq_len=1024,
            norm_eps=1e-6,
            tie_word_embeddings=False,
        )
