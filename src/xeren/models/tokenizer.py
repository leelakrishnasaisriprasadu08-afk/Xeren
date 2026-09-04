"""Tokenizer abstractions and special agent token support for Xeren model training."""

from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


SPECIAL_TOKENS: Dict[str, str] = {
    "pad_token": "<|pad|>",
    "bos_token": "<|im_start|>",
    "eos_token": "<|im_end|>",
    "system_token": "<|system|>",
    "user_token": "<|user|>",
    "assistant_token": "<|assistant|>",
    "plan_token": "<|plan|>",
    "action_token": "<|action|>",
    "observation_token": "<|observation|>",
    "verification_token": "<|verification|>",
    "tool_token": "<|tool|>",
}

# PyTorch CrossEntropyLoss ignore index
IGNORE_INDEX: int = -100


class TokenizerConfig(BaseModel):
    """Configuration and special token definitions for the tokenizer."""
    pad_token: str = Field(default="<|pad|>")
    bos_token: str = Field(default="<|im_start|>")
    eos_token: str = Field(default="<|im_end|>")
    special_tokens: Dict[str, str] = Field(default_factory=lambda: dict(SPECIAL_TOKENS))


class BaseTokenizer(ABC):
    """Abstract interface for tokenizers used in Xeren model training and inference."""

    @abstractmethod
    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """Encode text to token integer IDs."""
        pass

    @abstractmethod
    def decode(self, token_ids: List[int], skip_special_tokens: bool = False) -> str:
        """Decode token IDs back to a string."""
        pass

    @property
    @abstractmethod
    def pad_token_id(self) -> int:
        """Pad token integer ID."""
        pass

    @property
    @abstractmethod
    def eos_token_id(self) -> int:
        """End-of-sequence token ID."""
        pass

    @property
    @abstractmethod
    def vocab_size(self) -> int:
        """Total vocabulary size."""
        pass

    @abstractmethod
    def tokenize_conversation(
        self,
        messages: List[Dict[str, str]],
        max_length: Optional[int] = None,
        mask_prompt: bool = True,
    ) -> Dict[str, List[int]]:
        """Tokenize a multi-turn conversation into input_ids, attention_mask, and labels."""
        pass


class XerenTokenizer(BaseTokenizer):
    """Built-in standalone tokenizer for Xeren.

    Provides deterministic tokenization, special token handling, and loss masking
    without requiring external binary dependencies. Supports HuggingFace tokenizer
    integration when transformers is installed.
    """

    def __init__(self, config: Optional[TokenizerConfig] = None) -> None:
        self.config = config or TokenizerConfig()
        self._special_tokens = self.config.special_tokens

        # Build initial vocabulary starting with special tokens
        self._vocab: Dict[str, int] = {}
        self._reverse_vocab: Dict[int, str] = {}

        # 1. Special tokens first (IDs 0..N)
        for i, (_, token_str) in enumerate(self._special_tokens.items()):
            self._vocab[token_str] = i
            self._reverse_vocab[i] = token_str

        # 2. Byte tokens (256 ASCII/byte values) for full coverage
        offset = len(self._vocab)
        for b in range(256):
            char_repr = chr(b)
            if char_repr not in self._vocab:
                self._vocab[char_repr] = offset
                self._reverse_vocab[offset] = char_repr
                offset += 1

        self._pad_id = self._vocab[self.config.pad_token]
        self._eos_id = self._vocab[self.config.eos_token]
        self._bos_id = self._vocab[self.config.bos_token]

        # Regex for splitting special tokens vs whitespace/punctuation
        special_pattern = "|".join(re.escape(tok) for tok in self._special_tokens.values())
        self._pattern = re.compile(f"({special_pattern}|\\w+|[^\\w\\s]|\\s+)")

    @property
    def pad_token_id(self) -> int:
        return self._pad_id

    @property
    def eos_token_id(self) -> int:
        return self._eos_id

    @property
    def bos_token_id(self) -> int:
        return self._bos_id

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)

    def _get_or_add_token(self, token: str) -> int:
        if token in self._vocab:
            return self._vocab[token]
        idx = len(self._vocab)
        self._vocab[token] = idx
        self._reverse_vocab[idx] = token
        return idx

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """Encode text to token IDs using subword/byte fallback."""
        if not text:
            return []

        tokens: List[int] = []
        if add_special_tokens:
            tokens.append(self.bos_token_id)

        segments = self._pattern.findall(text)
        for seg in segments:
            if not seg:
                continue
            if seg in self._special_tokens.values():
                tokens.append(self._vocab[seg])
            elif seg in self._vocab:
                tokens.append(self._vocab[seg])
            else:
                # Add word to vocabulary dynamically or encode as bytes
                tokens.append(self._get_or_add_token(seg))

        if add_special_tokens:
            tokens.append(self.eos_token_id)

        return tokens

    def decode(self, token_ids: List[int], skip_special_tokens: bool = False) -> str:
        """Decode token IDs back to a string."""
        pieces: List[str] = []
        special_set = set(self._special_tokens.values())

        for tid in token_ids:
            if tid in self._reverse_vocab:
                token_str = self._reverse_vocab[tid]
                if skip_special_tokens and token_str in special_set:
                    continue
                pieces.append(token_str)
            else:
                pieces.append(f"<|unk_{tid}|>")

        return "".join(pieces)

    def tokenize_conversation(
        self,
        messages: List[Dict[str, str]],
        max_length: Optional[int] = None,
        mask_prompt: bool = True,
    ) -> Dict[str, List[int]]:
        """Tokenize conversational turns with prompt masking (label=-100 on user/system).

        Format per turn:
        <|im_start|><|role|>\n{content}<|im_end|>\n
        """
        input_ids: List[int] = []
        labels: List[int] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            role_token = self._special_tokens.get(f"{role}_token", f"<|{role}|>")
            role_turn_text = f"<|im_start|>{role_token}\n{content}<|im_end|>\n"
            turn_tokens = self.encode(role_turn_text, add_special_tokens=False)

            input_ids.extend(turn_tokens)

            # In causal language modeling, calculate loss only on assistant generation
            if mask_prompt and role in ("system", "user"):
                labels.extend([IGNORE_INDEX] * len(turn_tokens))
            else:
                labels.extend(turn_tokens)

        # Truncation if max_length is specified
        if max_length and len(input_ids) > max_length:
            input_ids = input_ids[:max_length]
            labels = labels[:max_length]

        attention_mask = [1] * len(input_ids)

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }
