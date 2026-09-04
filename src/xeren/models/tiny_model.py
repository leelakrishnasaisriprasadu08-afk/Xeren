"""Tiny standalone causal language model for deterministic training smoke tests."""

import math
import random
from typing import Any, Dict, List, Optional, Tuple


class TinyCausalLM:
    """A lightweight standalone causal language model with genuine trainable parameters.

    Supports forward pass, causal autoregressive cross-entropy loss with -100 masking,
    analytical backpropagation, and gradient descent parameter updates without requiring
    external machine learning dependencies.
    """

    def __init__(
        self,
        vocab_size: int = 500,
        hidden_dim: int = 16,
        seed: int = 42,
    ) -> None:
        self.vocab_size = max(10, vocab_size)
        self.hidden_dim = max(4, hidden_dim)
        self.seed = seed

        rng = random.Random(seed)
        scale = 1.0 / math.sqrt(self.hidden_dim)

        # Trainable parameters
        # 1. Embedding matrix: [vocab_size, hidden_dim]
        self.w_embed: List[List[float]] = [
            [rng.gauss(0.0, scale) for _ in range(self.hidden_dim)]
            for _ in range(self.vocab_size)
        ]
        # 2. Hidden projection matrix: [hidden_dim, hidden_dim]
        self.w_hidden: List[List[float]] = [
            [rng.gauss(0.0, scale) for _ in range(self.hidden_dim)]
            for _ in range(self.hidden_dim)
        ]
        # 3. Output projection head (LM head): [hidden_dim, vocab_size]
        self.w_out: List[List[float]] = [
            [rng.gauss(0.0, scale) for _ in range(self.vocab_size)]
            for _ in range(self.hidden_dim)
        ]
        # 4. Output bias: [vocab_size]
        self.b_out: List[float] = [0.0] * self.vocab_size

        self._cache: Dict[str, Any] = {}

    def forward(
        self,
        input_ids: List[List[int]],
        labels: Optional[List[List[int]]] = None,
    ) -> Tuple[List[List[List[float]]], float]:
        """Compute forward logits and shifted causal cross-entropy loss.

        Target tokens with label == -100 are ignored in the loss calculation.
        """
        B = len(input_ids)
        if B == 0:
            return [], 0.0

        T = len(input_ids[0])
        H = self.hidden_dim
        V = self.vocab_size

        z_all: List[List[List[float]]] = []
        h_all: List[List[List[float]]] = []
        logits_all: List[List[List[float]]] = []
        p_all: List[List[List[float]]] = []

        total_loss = 0.0
        n_unmasked = 0

        for b in range(B):
            z_seq: List[List[float]] = []
            h_seq: List[List[float]] = []
            logits_seq: List[List[float]] = []
            p_seq: List[List[float]] = []

            for t in range(T):
                token = input_ids[b][t]
                token_clamped = min(max(0, token), V - 1)
                h = self.w_embed[token_clamped]
                h_seq.append(h)

                # Linear + tanh hidden layer
                z = [0.0] * H
                for d in range(H):
                    val = sum(h[j] * self.w_hidden[j][d] for j in range(H))
                    z[d] = math.tanh(val)
                z_seq.append(z)

                # LM projection head to logits
                logits = [
                    self.b_out[v] + sum(z[d] * self.w_out[d][v] for d in range(H))
                    for v in range(V)
                ]
                logits_seq.append(logits)

                # Numerically stable softmax probabilities
                max_l = max(logits)
                exp_l = [math.exp(min(30.0, max(-30.0, lv - max_l))) for lv in logits]
                sum_exp = sum(exp_l)
                p = [ev / sum_exp for ev in exp_l]
                p_seq.append(p)

                # Causal next-token prediction loss: token at step t predicts label at step t + 1
                if labels is not None and t < T - 1:
                    target = labels[b][t + 1]
                    if target != -100 and 0 <= target < V:
                        prob_target = max(p[target], 1e-12)
                        total_loss += -math.log(prob_target)
                        n_unmasked += 1

            z_all.append(z_seq)
            h_all.append(h_seq)
            logits_all.append(logits_seq)
            p_all.append(p_seq)

        loss = (total_loss / n_unmasked) if n_unmasked > 0 else 0.0

        self._cache = {
            "input_ids": input_ids,
            "labels": labels,
            "z_all": z_all,
            "h_all": h_all,
            "p_all": p_all,
            "n_unmasked": n_unmasked,
        }

        return logits_all, loss

    def backward_and_step(self, lr: float = 0.01) -> None:
        """Perform analytical backpropagation and gradient descent parameter updates."""
        if "labels" not in self._cache or self._cache["n_unmasked"] == 0:
            return

        input_ids = self._cache["input_ids"]
        labels = self._cache["labels"]
        z_all = self._cache["z_all"]
        h_all = self._cache["h_all"]
        p_all = self._cache["p_all"]
        N = self._cache["n_unmasked"]

        B = len(input_ids)
        T = len(input_ids[0]) if B > 0 else 0
        H = self.hidden_dim
        V = self.vocab_size

        dw_embed: Dict[int, List[float]] = {}
        dw_hidden = [[0.0] * H for _ in range(H)]
        dw_out = [[0.0] * V for _ in range(H)]
        db_out = [0.0] * V

        # Compute analytical gradients
        for b in range(B):
            for t in range(T - 1):
                target = labels[b][t + 1]
                if target == -100 or not (0 <= target < V):
                    continue

                p = p_all[b][t]
                z = z_all[b][t]
                h = h_all[b][t]
                token = min(max(0, input_ids[b][t]), V - 1)

                dlogits = [0.0] * V
                for v in range(V):
                    grad = (p[v] - (1.0 if v == target else 0.0)) / N
                    dlogits[v] = grad
                    db_out[v] += grad
                    for d in range(H):
                        dw_out[d][v] += z[d] * grad

                dz = [
                    sum(dlogits[v] * self.w_out[d][v] for v in range(V))
                    for d in range(H)
                ]
                dact = [dz[d] * (1.0 - z[d] ** 2) for d in range(H)]

                for j in range(H):
                    for d in range(H):
                        dw_hidden[j][d] += h[j] * dact[d]

                dh = [
                    sum(dact[d] * self.w_hidden[j][d] for d in range(H))
                    for j in range(H)
                ]
                if token not in dw_embed:
                    dw_embed[token] = [0.0] * H
                for j in range(H):
                    dw_embed[token][j] += dh[j]

        # Optimizer step: Gradient descent with gradient clipping
        for d in range(H):
            for v in range(V):
                grad = min(max(dw_out[d][v], -5.0), 5.0)
                self.w_out[d][v] -= lr * grad

        for v in range(V):
            grad = min(max(db_out[v], -5.0), 5.0)
            self.b_out[v] -= lr * grad

        for j in range(H):
            for d in range(H):
                grad = min(max(dw_hidden[j][d], -5.0), 5.0)
                self.w_hidden[j][d] -= lr * grad

        for token, grads in dw_embed.items():
            for j in range(H):
                grad = min(max(grads[j], -5.0), 5.0)
                self.w_embed[token][j] -= lr * grad

    def state_dict(self) -> Dict[str, Any]:
        """Return model parameters for checkpoint persistence."""
        return {
            "vocab_size": self.vocab_size,
            "hidden_dim": self.hidden_dim,
            "w_embed": self.w_embed,
            "w_hidden": self.w_hidden,
            "w_out": self.w_out,
            "b_out": self.b_out,
        }

    def load_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore model parameters from checkpoint dictionary."""
        self.vocab_size = state["vocab_size"]
        self.hidden_dim = state["hidden_dim"]
        self.w_embed = state["w_embed"]
        self.w_hidden = state["w_hidden"]
        self.w_out = state["w_out"]
        self.b_out = state["b_out"]
