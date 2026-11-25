"""Custom Byte-Pair Encoding (BPE) Tokenizer for Xeren LLM.

Trains a vocabulary from scratch with native support for Xeren's agent and reasoning
special tokens.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
from tokenizers.processors import TemplateProcessing

SPECIAL_TOKENS = [
    "<|pad|>",
    "<|unk|>",
    "<|bos|>",
    "<|eos|>",
    "<|im_start|>",
    "<|im_end|>",
    "<|thought|>",
    "<|plan|>",
    "<|tool_call|>",
    "<|tool_result|>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",
]


class XerenTokenizer:
    """Wrapper around trained HuggingFace BPE Tokenizer with Xeren chat formatting."""

    def __init__(self, tokenizer: Tokenizer):
        self._tokenizer = tokenizer
        self.pad_token = "<|pad|>"
        self.unk_token = "<|unk|>"
        self.bos_token = "<|bos|>"
        self.eos_token = "<|eos|>"
        self.pad_token_id = self._tokenizer.token_to_id(self.pad_token)
        self.unk_token_id = self._tokenizer.token_to_id(self.unk_token)
        self.bos_token_id = self._tokenizer.token_to_id(self.bos_token)
        self.eos_token_id = self._tokenizer.token_to_id(self.eos_token)
        self.vocab_size = self._tokenizer.get_vocab_size()

    @classmethod
    def train_from_iterator(
        cls,
        iterator: Iterator[str],
        vocab_size: int = 16384,
        min_frequency: int = 2,
    ) -> "XerenTokenizer":
        """Train a byte-level BPE tokenizer from an in-memory string iterator."""
        tokenizer = Tokenizer(models.BPE(unk_token="<|unk|>"))
        tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tokenizer.decoder = decoders.ByteLevel()

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=SPECIAL_TOKENS,
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        )

        tokenizer.train_from_iterator(iterator, trainer=trainer)
        return cls(tokenizer)

    @classmethod
    def train_from_files(
        cls,
        files: List[str],
        vocab_size: int = 16384,
        min_frequency: int = 2,
    ) -> "XerenTokenizer":
        """Train a byte-level BPE tokenizer from text files."""
        tokenizer = Tokenizer(models.BPE(unk_token="<|unk|>"))
        tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tokenizer.decoder = decoders.ByteLevel()

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=SPECIAL_TOKENS,
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        )

        tokenizer.train(files, trainer=trainer)
        return cls(tokenizer)

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """Encode text to token IDs."""
        encoding = self._tokenizer.encode(text)
        ids = encoding.ids
        if add_special_tokens and self.bos_token_id is not None:
            ids = [self.bos_token_id] + ids
        return ids

    def decode(self, token_ids: List[int], skip_special_tokens: bool = False) -> str:
        """Decode token IDs back to text."""
        return self._tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)

    def format_chat(self, messages: List[Dict[str, str]]) -> str:
        """Format a list of chat message dicts into Xeren ChatML format."""
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
        return formatted

    def save(self, directory: Union[str, Path]) -> None:
        """Save tokenizer configuration and model files."""
        os.makedirs(directory, exist_ok=True)
        dir_path = Path(directory)
        self._tokenizer.save(str(dir_path / "tokenizer.json"))

        metadata = {
            "name": "XerenTokenizer",
            "vocab_size": self.vocab_size,
            "special_tokens": SPECIAL_TOKENS,
            "pad_token_id": self.pad_token_id,
            "unk_token_id": self.unk_token_id,
            "bos_token_id": self.bos_token_id,
            "eos_token_id": self.eos_token_id,
        }
        with open(dir_path / "tokenizer_config.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    @classmethod
    def load(cls, directory: Union[str, Path]) -> "XerenTokenizer":
        """Load tokenizer from directory."""
        dir_path = Path(directory)
        json_file = dir_path / "tokenizer.json"
        if not json_file.exists():
            raise FileNotFoundError(f"Tokenizer file not found at {json_file}")
        tokenizer = Tokenizer.from_file(str(json_file))
        return cls(tokenizer)
