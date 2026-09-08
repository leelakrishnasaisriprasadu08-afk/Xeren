"""Custom PyTorch Decoder-Only Transformer Architecture for Xeren LM.

Core Architecture:
- RMSNorm (Root Mean Square Layer Normalization)
- Rotary Position Embeddings (RoPE) with extended theta for Stage 2
- SwiGLU feedforward activation
- Grouped Query Attention (GQA)
- PyTorch Scaled Dot-Product Attention (SDPA)
- Native KV-Caching for fast autoregressive generation

Stage 2 Domain-Specialization Heads:
- PluginClassificationHead: Predicts which Xeren plugin to dispatch
- ConfidenceScoreHead: Calibrated probability output [0.0-1.0]
- ThreatClassificationHead: Malware / security threat detection
"""

import math
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from training.src.model.config import XerenConfig


# =============================================================================
# Core Building Blocks
# =============================================================================

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
    assert freqs_cis.shape == (x.shape[1], x.shape[-1]), \
        f"freqs_cis shape {freqs_cis.shape} != {(x.shape[1], x.shape[-1])}"
    shape = [d if i == 1 or i == ndim - 1 else 1 for i, d in enumerate(x.shape)]
    return freqs_cis.view(*shape)


def apply_rotary_emb(
    xq: torch.Tensor,
    xk: torch.Tensor,
    freqs_cis: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
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


# =============================================================================
# Attention + FFN Blocks
# =============================================================================

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

        key = repeat_kv(xk, self.n_rep)
        value = repeat_kv(xv, self.n_rep)

        query = xq.transpose(1, 2)
        key = key.transpose(1, 2)
        value = value.transpose(1, 2)

        is_causal = mask is None and seqlen > 1
        output = F.scaled_dot_product_attention(
            query, key, value,
            attn_mask=mask,
            dropout_p=self.dropout.p if self.training else 0.0,
            is_causal=is_causal,
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


# =============================================================================
# Stage 2 Domain-Specialization Heads
# =============================================================================

# Xeren plugin names (index → plugin name)
PLUGIN_NAMES: List[str] = [
    "research",       # 0 - Web search, RAG retrieval
    "coding",         # 1 - Code generation, execution
    "file",           # 2 - File read/write/manage
    "browser",        # 3 - Web browsing, scraping
    "api",            # 4 - REST/GraphQL API calls
    "conversation",   # 5 - General conversation
    "data",           # 6 - Data analysis, transforms
    "knowledge",      # 7 - Knowledge base queries
    "website",        # 8 - Website generation
]

# Threat class names (index → threat type)
THREAT_CLASS_NAMES: List[str] = [
    "clean",          # 0 - Safe, no threat
    "malware",        # 1 - General malware
    "shellcode",      # 2 - Shellcode / exploit payload
    "phishing",       # 3 - Phishing / social engineering
    "exploit",        # 4 - Known CVE exploit attempt
    "suspicious",     # 5 - Suspicious but unconfirmed
]


class PluginClassificationHead(nn.Module):
    """Predicts which Xeren plugin should be dispatched for a given context.
    
    Takes the final hidden state [CLS-equivalent = last token representation]
    and outputs a probability distribution over all Xeren plugins.
    
    Used during: plugin routing at inference, plugin loss during Stage 2 training.
    """

    def __init__(self, dim: int, num_plugins: int = 9, dropout: float = 0.1):
        super().__init__()
        self.norm = RMSNorm(dim)
        self.fc1 = nn.Linear(dim, dim // 2, bias=True)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dim // 2, num_plugins, bias=True)
        self.plugin_names = PLUGIN_NAMES[:num_plugins]

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        """
        Args:
            hidden: (batch, dim) — last token's hidden state
        Returns:
            logits: (batch, num_plugins) — raw plugin logits
        """
        x = self.norm(hidden)
        x = self.dropout(self.act(self.fc1(x)))
        return self.fc2(x)

    def predict(self, hidden: torch.Tensor) -> Dict:
        """Return plugin prediction with probabilities."""
        logits = self.forward(hidden)
        probs = torch.softmax(logits, dim=-1)
        pred_idx = probs.argmax(dim=-1).item()
        return {
            "plugin": self.plugin_names[pred_idx],
            "confidence": probs[0, pred_idx].item(),
            "all_probs": {
                name: probs[0, i].item()
                for i, name in enumerate(self.plugin_names)
            },
        }


class ConfidenceScoreHead(nn.Module):
    """Outputs a calibrated confidence score [0.0–1.0] for the model's generation.
    
    Enables Xeren to express uncertainty:
    - Score > 0.85: High confidence, proceed normally
    - Score 0.60–0.85: Moderate confidence, flag for review
    - Score < 0.60: Low confidence, trigger RAG retrieval fallback
    
    Used during: every generation step in Stage 2 inference.
    """

    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = RMSNorm(dim)
        self.fc1 = nn.Linear(dim, dim // 4, bias=True)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dim // 4, 1, bias=True)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        """
        Args:
            hidden: (batch, dim) — last token's hidden state
        Returns:
            score: (batch, 1) — confidence score in [0, 1]
        """
        x = self.norm(hidden)
        x = self.dropout(self.act(self.fc1(x)))
        return torch.sigmoid(self.fc2(x))


class ThreatClassificationHead(nn.Module):
    """Binary + multi-class threat classifier for malware and security analysis.
    
    Two outputs:
    1. is_threat (binary): Is this content malicious?
    2. threat_type (6-class): If threat, what category?
    
    Trained on WildGuard, MMLU security subset, and curated CVE/security examples.
    Used during: security analysis plugin calls and proactive content screening.
    """

    def __init__(self, dim: int, num_threat_classes: int = 6, dropout: float = 0.1):
        super().__init__()
        self.norm = RMSNorm(dim)
        self.fc1 = nn.Linear(dim, dim // 2, bias=True)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)

        # Binary head: clean vs threat
        self.binary_head = nn.Linear(dim // 2, 2, bias=True)

        # Multi-class head: threat category
        self.class_head = nn.Linear(dim // 2, num_threat_classes, bias=True)
        self.threat_names = THREAT_CLASS_NAMES[:num_threat_classes]

    def forward(self, hidden: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            hidden: (batch, dim) — last token's hidden state
        Returns:
            binary_logits: (batch, 2) — [clean, threat] logits
            class_logits: (batch, num_threat_classes) — threat type logits
        """
        x = self.norm(hidden)
        x = self.dropout(self.act(self.fc1(x)))
        return self.binary_head(x), self.class_head(x)

    def predict(self, hidden: torch.Tensor) -> Dict:
        """Return threat prediction with confidence scores."""
        bin_logits, cls_logits = self.forward(hidden)
        bin_probs = torch.softmax(bin_logits, dim=-1)
        cls_probs = torch.softmax(cls_logits, dim=-1)
        is_threat = bin_probs[0, 1].item() > 0.5
        threat_idx = cls_probs.argmax(dim=-1).item()
        return {
            "is_threat": is_threat,
            "threat_probability": bin_probs[0, 1].item(),
            "threat_type": self.threat_names[threat_idx] if is_threat else "clean",
            "threat_type_confidence": cls_probs[0, threat_idx].item(),
            "all_threat_probs": {
                name: cls_probs[0, i].item()
                for i, name in enumerate(self.threat_names)
            },
        }


# =============================================================================
# Main XerenTransformer Model
# =============================================================================

class XerenTransformer(nn.Module):
    """Xeren decoder-only transformer with optional domain-specialization heads.
    
    Stage 1: Pure language model — LM head only.
    Stage 2: Language model + Plugin + Confidence + Threat heads.
    """

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

        # Stage 2 domain-specialization heads (only created when enabled in config)
        self.plugin_head: Optional[PluginClassificationHead] = None
        self.confidence_head: Optional[ConfidenceScoreHead] = None
        self.threat_head: Optional[ThreatClassificationHead] = None

        if config.enable_plugin_head:
            self.plugin_head = PluginClassificationHead(
                dim=config.dim,
                num_plugins=config.num_plugins,
                dropout=config.dropout,
            )
        if config.enable_confidence_head:
            self.confidence_head = ConfidenceScoreHead(
                dim=config.dim,
                dropout=config.dropout,
            )
        if config.enable_threat_head:
            self.threat_head = ThreatClassificationHead(
                dim=config.dim,
                num_threat_classes=config.num_threat_classes,
                dropout=config.dropout,
            )

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

    def enable_gradient_checkpointing(self):
        """Enable gradient checkpointing to save VRAM during Stage 2 training."""
        for layer in self.layers:
            layer.attention.wq.weight.requires_grad_(True)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
        plugin_labels: Optional[torch.Tensor] = None,
        threat_labels: Optional[torch.Tensor] = None,
        start_pos: int = 0,
        kv_caches: Optional[list] = None,
    ) -> Dict:
        """
        Forward pass for XerenTransformer.

        Args:
            input_ids:      (batch, seq_len)
            labels:         (batch, seq_len) — LM next-token labels, -100 to ignore
            plugin_labels:  (batch,) — plugin class index for plugin head loss (Stage 2)
            threat_labels:  (batch,) — threat class index for threat head loss (Stage 2)
            start_pos:      Start index for RoPE in autoregressive mode
            kv_caches:      Optional list of KV caches per layer

        Returns:
            dict with keys:
              logits          — (batch, seq_len, vocab_size)
              loss            — scalar or None (LM loss)
              plugin_logits   — (batch, num_plugins) or None
              plugin_loss     — scalar or None
              confidence      — (batch, 1) score or None
              threat_logits   — (binary_logits, class_logits) or None
              threat_loss     — scalar or None
              total_loss      — weighted sum of all active losses or None
              new_kv_caches   — updated KV cache list
        """
        bsz, seqlen = input_ids.shape
        h = self.tok_embeddings(input_ids)

        freqs_cis = self.freqs_cis[start_pos: start_pos + seqlen]

        new_kv_caches = [] if kv_caches is not None else None
        for i, layer in enumerate(self.layers):
            cache_i = kv_caches[i] if kv_caches is not None else None
            h, new_cache = layer(h, freqs_cis, kv_cache=cache_i)
            if new_kv_caches is not None:
                new_kv_caches.append(new_cache)

        h = self.norm(h)
        logits = self.output(h)

        # Last token hidden state — used by all specialization heads
        last_hidden = h[:, -1, :]  # (batch, dim)

        # ---- Language Modeling Loss ----
        lm_loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            lm_loss = F.cross_entropy(
                shift_logits.view(-1, self.config.vocab_size),
                shift_labels.view(-1),
                ignore_index=-100,
            )

        # ---- Plugin Classification Head (Stage 2) ----
        plugin_logits = None
        plugin_loss = None
        if self.plugin_head is not None:
            plugin_logits = self.plugin_head(last_hidden)
            if plugin_labels is not None:
                plugin_loss = F.cross_entropy(plugin_logits, plugin_labels)

        # ---- Confidence Score Head (Stage 2) ----
        confidence_score = None
        if self.confidence_head is not None:
            confidence_score = self.confidence_head(last_hidden)

        # ---- Threat Classification Head (Stage 2) ----
        threat_logits = None
        threat_loss = None
        if self.threat_head is not None:
            bin_logits, cls_logits = self.threat_head(last_hidden)
            threat_logits = (bin_logits, cls_logits)
            if threat_labels is not None:
                # Binary: is it a threat (label >= 1 means threat)
                binary_labels = (threat_labels > 0).long()
                threat_loss = (
                    F.cross_entropy(bin_logits, binary_labels) * 0.5 +
                    F.cross_entropy(cls_logits, threat_labels) * 0.5
                )

        # ---- Total Weighted Loss (Stage 2 multi-task) ----
        total_loss = None
        if lm_loss is not None:
            total_loss = lm_loss
            if plugin_loss is not None:
                total_loss = total_loss + 0.3 * plugin_loss   # Plugin loss weight
            if threat_loss is not None:
                total_loss = total_loss + 0.2 * threat_loss   # Threat loss weight

        return {
            "logits": logits,
            "loss": lm_loss,
            "total_loss": total_loss,
            "plugin_logits": plugin_logits,
            "plugin_loss": plugin_loss,
            "confidence": confidence_score,
            "threat_logits": threat_logits,
            "threat_loss": threat_loss,
            "new_kv_caches": new_kv_caches,
        }

    def predict_plugin(self, input_ids: torch.Tensor) -> Optional[Dict]:
        """Convenience method: run forward and return plugin prediction."""
        if self.plugin_head is None:
            return None
        with torch.no_grad():
            out = self.forward(input_ids)
            last_hidden = out["logits"][:, -1, :] * 0  # reuse last_hidden
            # Re-extract last hidden before output projection
            h = self.tok_embeddings(input_ids)
            freqs_cis = self.freqs_cis[:input_ids.shape[1]]
            for layer in self.layers:
                h, _ = layer(h, freqs_cis)
            h = self.norm(h)
            return self.plugin_head.predict(h[:, -1, :])

    def predict_threat(self, input_ids: torch.Tensor) -> Optional[Dict]:
        """Convenience method: run forward and return threat analysis."""
        if self.threat_head is None:
            return None
        with torch.no_grad():
            h = self.tok_embeddings(input_ids)
            freqs_cis = self.freqs_cis[:input_ids.shape[1]]
            for layer in self.layers:
                h, _ = layer(h, freqs_cis)
            h = self.norm(h)
            return self.threat_head.predict(h[:, -1, :])
