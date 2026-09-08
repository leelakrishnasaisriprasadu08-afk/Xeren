"""Inference and text generation module for Xeren LLM."""

from typing import Iterator, List, Optional
import torch
import torch.nn.functional as F

from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer


def top_k_top_p_filtering(
    logits: torch.Tensor,
    top_k: int = 50,
    top_p: float = 0.9,
    filter_value: float = -float("Inf"),
) -> torch.Tensor:
    """Filter logits using top-k and/or nucleus (top-p) sampling."""
    if top_k > 0:
        top_k = min(top_k, logits.size(-1))
        indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
        logits[indices_to_remove] = filter_value

    if top_p < 1.0:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

        # Remove tokens with cumulative probability above the threshold
        sorted_indices_to_remove = cumulative_probs > top_p
        # Shift the indices to the right to keep also the first token above the threshold
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0

        indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
        logits[indices_to_remove] = filter_value

    return logits


class XerenGenerator:
    def __init__(
        self,
        model: XerenTransformer,
        tokenizer: XerenTokenizer,
        device: str = "cpu",
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = torch.device(device)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9,
    ) -> str:
        """Autoregressively generate a completion for a prompt."""
        input_ids = self.tokenizer.encode(prompt, add_special_tokens=True)
        tokens = torch.tensor([input_ids], dtype=torch.long, device=self.device)

        generated = list(input_ids)
        eos_id = self.tokenizer.eos_token_id

        # Initial forward pass to populate KV cache
        kv_caches = None
        logits, _, kv_caches = self.model(tokens, kv_caches=kv_caches)
        next_token_logits = logits[:, -1, :]

        for _ in range(max_new_tokens):
            if temperature == 0.0:
                next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
            else:
                scaled_logits = next_token_logits / temperature
                filtered_logits = top_k_top_p_filtering(scaled_logits, top_k=top_k, top_p=top_p)
                probs = F.softmax(filtered_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)

            token_val = int(next_token.item())
            if token_val == eos_id:
                break

            generated.append(token_val)

            # Fast step using KV cache
            start_pos = len(generated) - 1
            logits, _, kv_caches = self.model(next_token, start_pos=start_pos, kv_caches=kv_caches)
            next_token_logits = logits[:, -1, :]

        return self.tokenizer.decode(generated, skip_special_tokens=False)

    @torch.no_grad()
    def stream_generate(
        self,
        prompt: str,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9,
    ) -> Iterator[str]:
        """Stream generated completion tokens."""
        input_ids = self.tokenizer.encode(prompt, add_special_tokens=True)
        tokens = torch.tensor([input_ids], dtype=torch.long, device=self.device)

        eos_id = self.tokenizer.eos_token_id
        kv_caches = None
        logits, _, kv_caches = self.model(tokens, kv_caches=kv_caches)
        next_token_logits = logits[:, -1, :]

        start_pos = len(input_ids)
        for _ in range(max_new_tokens):
            if temperature == 0.0:
                next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
            else:
                scaled_logits = next_token_logits / temperature
                filtered_logits = top_k_top_p_filtering(scaled_logits, top_k=top_k, top_p=top_p)
                probs = F.softmax(filtered_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)

            token_val = int(next_token.item())
            if token_val == eos_id:
                break

            yield self.tokenizer.decode([token_val], skip_special_tokens=False)

            logits, _, kv_caches = self.model(next_token, start_pos=start_pos, kv_caches=kv_caches)
            next_token_logits = logits[:, -1, :]
            start_pos += 1
