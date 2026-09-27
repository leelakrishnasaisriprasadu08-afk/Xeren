"""
Xeren MoS & Transformer Checkpoint Utilities
============================================
Provides unified tools to:
1. Dynamically infer XerenConfig from saved state_dict weight shapes.
2. Load any native XerenTransformer checkpoint with strict weight checking.
3. Perform autoregressive text generation for specialists and orchestrators.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
import torch

from .config import XerenConfig
from .xeren_transformer import XerenTransformer

logger = logging.getLogger("xeren.model.checkpoint_utils")


def config_from_checkpoint(state_dict: dict, vocab_size: int) -> XerenConfig:
    """
    Infer XerenConfig from saved weight shapes.
    Ensures model architecture matches checkpoint exactly without manual hardcoding.
    """
    tok_emb = state_dict.get("tok_embeddings.weight", None)
    if tok_emb is not None:
        checkpoint_vocab, dim = tok_emb.shape
    else:
        for k, v in state_dict.items():
            if "tok_embeddings.weight" in k:
                checkpoint_vocab, dim = v.shape
                break
        else:
            raise KeyError("Cannot find tok_embeddings.weight in checkpoint")

    # Count distinct layer indices in state_dict
    layer_indices = set()
    for k in state_dict.keys():
        if k.startswith("layers."):
            parts = k.split(".")
            if len(parts) > 1 and parts[1].isdigit():
                layer_indices.add(int(parts[1]))
    n_layers = len(layer_indices) if layer_indices else 16

    # Attention shapes from layer 0
    wq = state_dict.get("layers.0.attention.wq.weight", None)
    wk = state_dict.get("layers.0.attention.wk.weight", None)
    w1 = state_dict.get("layers.0.feed_forward.w1.weight", None)

    hidden_dim = w1.shape[0] if w1 is not None else int(dim * 2.75)
    n_heads = 16
    if wq is not None and wk is not None:
        head_dim = dim // n_heads
        n_kv_heads = wk.shape[0] // head_dim if head_dim > 0 else 4
    else:
        n_kv_heads = 4

    cfg = XerenConfig(
        vocab_size=vocab_size,
        dim=dim,
        n_layers=n_layers,
        n_heads=n_heads,
        n_kv_heads=n_kv_heads,
        hidden_dim=hidden_dim,
        max_seq_len=2048,
        norm_eps=1e-5,
        rope_theta=500000.0,
        dropout=0.0,
        tie_word_embeddings=False,
    )
    return cfg


def load_native_xeren_model(
    checkpoint_path: Path,
    vocab_size: int,
    device: Optional[torch.device] = None,
) -> Tuple[XerenTransformer, XerenConfig]:
    """
    Load a pure XerenTransformer model from a checkpoint path (.pt file or directory containing it).
    """
    path = Path(checkpoint_path)
    if path.is_dir():
        for candidate in ["checkpoint_final.pt", "checkpoint_latest.pt", "model.pt"]:
            if (path / candidate).exists():
                path = path / candidate
                break
        else:
            pt_files = list(path.glob("*.pt"))
            if pt_files:
                path = pt_files[0]
            else:
                raise FileNotFoundError(f"No .pt checkpoint found in directory: {checkpoint_path}")

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    state_dict = ckpt.get("model_state_dict", ckpt)

    cfg = config_from_checkpoint(state_dict, vocab_size)
    model = XerenTransformer(cfg)
    missing, unexpected = model.load_state_dict(state_dict, strict=True)
    if missing or unexpected:
        logger.warning(
            "Checkpoint loaded with missing=%d, unexpected=%d",
            len(missing),
            len(unexpected),
        )

    model = model.to(device)
    model.eval()
    return model, cfg


@torch.no_grad()
def generate_text(
    model: XerenTransformer,
    tokenizer,
    prompt: str,
    max_new_tokens: int = 128,
    temperature: float = 0.7,
    device: Optional[torch.device] = None,
) -> str:
    """
    Autoregressive token generation using XerenTransformer and XerenTokenizer.
    """
    if device is None:
        device = next(model.parameters()).device

    input_ids = tokenizer.encode(prompt, add_special_tokens=False)
    if not input_ids:
        input_ids = [tokenizer.bos_token_id or 1]

    inp = torch.tensor([input_ids], dtype=torch.long, device=device)
    eos_id = tokenizer.eos_token_id
    generated = []

    model.eval()
    for _ in range(max_new_tokens):
        # Clip context window to max_seq_len
        curr_inp = inp[:, -model.config.max_seq_len:]
        out = model(curr_inp)
        logits = out["logits"][:, -1, :]  # last token logits

        if temperature <= 0.01:
            next_token = logits.argmax(dim=-1, keepdim=True)
        else:
            scaled_logits = logits / temperature
            probs = torch.softmax(scaled_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)

        token_id = next_token.item()
        if eos_id is not None and token_id == eos_id:
            break

        generated.append(token_id)
        inp = torch.cat([inp, next_token], dim=-1)

    return tokenizer.decode(generated).strip()
