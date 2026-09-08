"""Custom PyTorch Decoder-Only Transformer Architecture for Xeren LM.

Features:
- RMSNorm (Root Mean Square Layer Normalization)
- Rotary Position Embeddings (RoPE)
- SwiGLU feedforward activation
- Grouped Query Attention (GQA)
- PyTorch Scaled Dot-Product Attention (SDPA)
- Native KV-Caching for fast autoregressive generation
"""

import math
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from training.src.model.config import XerenConfig


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output = self._norm(x.float()).type_as(x)
        return output * self.weight


def precompute_freqs_cis(dim: int, end: int, theta: float = 10000.0) -> torch.Tensor:
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))
    t = torch.arange(end, device=freqs.device, dtype=torch.float32)
    freqs = torch.outer(t, freqs)
    freqs_cis = torch.polar(torch.ones_like(freqs), freqs)  # complex64
    return freqs_cis


def reshape_for_broadcast(freqs_cis: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    ndim = x.ndim
    assert 0 <= 1 < ndim
    assert freqs_cis.shape == (x.shape[1], x.shape[-1]), f"freqs_cis shape {freqs_cis.shape} != {(x.shape[1], x.shape[-1])}"
    shape = [d if i == 1 or i == ndim - 1 else 1 for i, d in enumerate(x.shape)]
    return freqs_cis.view(*shape)


def apply_rotary_emb(
    xq: torch.Tensor,
    xk: torch.Tensor,
    freqs_cis: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    # xq: (B, S, H, D), xk: (B, S, H_kv, D)
    xq_ = torch.view_as_complex(xq.float().reshape(*xq.shape[:-1], -1, 2))
    xk_ = torch.view_as_complex(xk.float().reshape(*xk.shape[:-1], -1, 2))
    freqs_cis = reshape_for_broadcast(freqs_cis, xq_)
    xq_out = torch.view_as_real(xq_ * freqs_cis).flatten(3)
    xk_out = torch.view_as_real(xk_ * freqs_cis).flatten(3)
    return xq_out.type_as(xq), xk_out.type_as(xk)


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """Repeat key/value heads along head dimension when using Grouped Query Attention."""
    if n_rep == 1:
        return x
    bs, seqlen, n_kv_heads, head_dim = x.shape
    return (
        x[:, :, :, None, :]
        .expand(bs, seqlen, n_kv_heads, n_rep, head_dim)
        .reshape(bs, seqlen, n_kv_heads * n_rep, head_dim)
    )


class GroupedQueryAttention(nn.Module):
    def __init__(self, config: XerenConfig):
        super().__init__()
        self.n_heads = config.n_heads
        self.n_kv_heads = config.n_kv_heads
        self.n_rep = self.n_heads // self.n_kv_heads
        self.head_dim = config.dim // config.n_heads
        self.dim = config.dim

        self.wq = nn.Linear(config.dim, config.n_heads * self.head_dim, bias=False)
        self.wk = nn.Linear(config.dim, self.n_kv_heads * self.head_dim, bias=False)
        self.wv = nn.Linear(config.dim, self.n_kv_heads * self.head_dim, bias=False)
        self.wo = nn.Linear(config.n_heads * self.head_dim, config.dim, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(
        self,
        x: torch.Tensor,
        freqs_cis: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        bsz, seqlen, _ = x.shape

        xq = self.wq(x).view(bsz, seqlen, self.n_heads, self.head_dim)
        xk = self.wk(x).view(bsz, seqlen, self.n_kv_heads, self.head_dim)
        xv = self.wv(x).view(bsz, seqlen, self.n_kv_heads, self.head_dim)

        xq, xk = apply_rotary_emb(xq, xk, freqs_cis=freqs_cis)

        # KV caching for inference
        if kv_cache is not None:
            prev_k, prev_v = kv_cache
            xk = torch.cat([prev_k, xk], dim=1)
            xv = torch.cat([prev_v, xv], dim=1)
            new_kv_cache = (xk, xv)
        else:
            new_kv_cache = None

        # Repeat KV for GQA
        key = repeat_kv(xk, self.n_rep)
        value = repeat_kv(xv, self.n_rep)

        # Transpose for SDPA: (bsz, n_heads, seqlen, head_dim)
        query = xq.transpose(1, 2)
        key = key.transpose(1, 2)
        value = value.transpose(1, 2)

        is_causal = mask is None and seqlen > 1
        output = F.scaled_dot_product_attention(
            query, key, value, attn_mask=mask, dropout_p=self.dropout.p if self.training else 0.0, is_causal=is_causal
        )

        output = output.transpose(1, 2).contiguous().view(bsz, seqlen, -1)
        return self.wo(output), new_kv_cache


class SwiGLU(nn.Module):
    def __init__(self, config: XerenConfig):
        super().__init__()
        self.w1 = nn.Linear(config.dim, config.hidden_dim, bias=False)  # Gate
        self.w2 = nn.Linear(config.hidden_dim, config.dim, bias=False)  # Down
        self.w3 = nn.Linear(config.dim, config.hidden_dim, bias=False)  # Up

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class TransformerBlock(nn.Module):
    def __init__(self, config: XerenConfig):
        super().__init__()
        self.attention_norm = RMSNorm(config.dim, eps=config.norm_eps)
        self.attention = GroupedQueryAttention(config)
        self.ffn_norm = RMSNorm(config.dim, eps=config.norm_eps)
        self.feed_forward = SwiGLU(config)

    def forward(
        self,
        x: torch.Tensor,
        freqs_cis: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        h, new_kv = self.attention(self.attention_norm(x), freqs_cis, mask=mask, kv_cache=kv_cache)
        x = x + h
        x = x + self.feed_forward(self.ffn_norm(x))
        return x, new_kv


class XerenTransformer(nn.Module):
    def __init__(self, config: XerenConfig):
        super().__init__()
        self.config = config
        self.tok_embeddings = nn.Embedding(config.vocab_size, config.dim)

        self.layers = nn.ModuleList([TransformerBlock(config) for _ in range(config.n_layers)])
        self.norm = RMSNorm(config.dim, eps=config.norm_eps)
        self.output = nn.Linear(config.dim, config.vocab_size, bias=False)

        if config.tie_word_embeddings:
            self.output.weight = self.tok_embeddings.weight

        # Precompute RoPE complex frequencies
        head_dim = config.dim // config.n_heads
        freqs_cis = precompute_freqs_cis(head_dim, config.max_seq_len * 2, config.rope_theta)
        self.register_buffer("freqs_cis", freqs_cis, persistent=False)

        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module):
        """Custom weight initialization scaled by depth."""
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02 / math.sqrt(2 * self.config.n_layers))
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def count_parameters(self) -> int:
        """Calculate total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
        start_pos: int = 0,
        kv_caches: Optional[list] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[list]]:
        """
        Forward pass for XerenTransformer.
        
        Args:
            input_ids: Tensor of shape (batch_size, seq_len)
            labels: Optional Tensor of shape (batch_size, seq_len) for computing CrossEntropyLoss
            start_pos: Start index for RoPE in autoregressive mode
            kv_caches: Optional list of KV caches for each layer
            
        Returns:
            logits: (batch_size, seq_len, vocab_size)
            loss: CrossEntropyLoss scalar if labels is provided, else None
            new_kv_caches: Updated KV cache list for generation
        """
        bsz, seqlen = input_ids.shape
        h = self.tok_embeddings(input_ids)

        freqs_cis = self.freqs_cis[start_pos : start_pos + seqlen]

        new_kv_caches = [] if kv_caches is not None else None
        for i, layer in enumerate(self.layers):
            cache_i = kv_caches[i] if kv_caches is not None else None
            h, new_cache = layer(h, freqs_cis, kv_cache=cache_i)
            if new_kv_caches is not None:
                new_kv_caches.append(new_cache)

        h = self.norm(h)
        logits = self.output(h)

        loss = None
        if labels is not None:
            # Shift so that tokens < n predict n
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(
                shift_logits.view(-1, self.config.vocab_size),
                shift_labels.view(-1),
                ignore_index=-100,
            )

        return logits, loss, new_kv_caches
