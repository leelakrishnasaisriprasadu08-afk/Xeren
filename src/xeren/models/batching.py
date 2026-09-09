"""Batching, dynamic padding, and collator utilities for Xeren training."""

import random
from typing import Any, Dict, Iterator, List, Optional, Union
from pydantic import BaseModel, Field

from xeren.models.tokenizer import IGNORE_INDEX, BaseTokenizer, XerenTokenizer


class Batch(BaseModel):
    """Container for tokenized and padded input batches."""
    input_ids: List[List[int]]
    attention_mask: List[List[int]]
    labels: Optional[List[List[int]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return batch representation as dictionary."""
        return self.model_dump()

    def to_torch_tensors(self, device: Optional[str] = None) -> Dict[str, Any]:
        """Convert batch to PyTorch tensor dictionary if torch is installed."""
        try:
            import torch
            tensors = {
                "input_ids": torch.tensor(self.input_ids, dtype=torch.long),
                "attention_mask": torch.tensor(self.attention_mask, dtype=torch.long),
            }
            if self.labels is not None:
                tensors["labels"] = torch.tensor(self.labels, dtype=torch.long)
            if device and device != "auto":
                tensors = {k: v.to(device) for k, v in tensors.items()}
            return tensors
        except ImportError:
            raise RuntimeError("PyTorch is not installed. Use to_dict() for standard data structures.")


class DataCollatorForCausalLM:
    """Collator that dynamically pads tokenized sequences to the maximum length in each batch."""

    def __init__(
        self,
        pad_token_id: int,
        label_pad_token_id: int = IGNORE_INDEX,
        max_length: Optional[int] = None,
    ) -> None:
        self.pad_token_id = pad_token_id
        self.label_pad_token_id = label_pad_token_id
        self.max_length = max_length

    def collate(self, features: List[Dict[str, List[int]]]) -> Batch:
        """Pad variable-length sequence features into a uniform Batch."""
        if not features:
            return Batch(input_ids=[], attention_mask=[], labels=[])

        # Compute max length for this batch
        batch_max = max(len(f["input_ids"]) for f in features)
        if self.max_length:
            batch_max = min(batch_max, self.max_length)

        padded_input_ids: List[List[int]] = []
        padded_attention_masks: List[List[int]] = []
        padded_labels: Optional[List[List[int]]] = [] if "labels" in features[0] else None

        for f in features:
            ids = f["input_ids"][:batch_max]
            pad_len = batch_max - len(ids)

            # Pad inputs with pad_token_id
            padded_ids = ids + [self.pad_token_id] * pad_len
            padded_input_ids.append(padded_ids)

            # Pad attention mask with 0
            mask = f.get("attention_mask", [1] * len(ids))[:batch_max]
            padded_mask = mask + [0] * pad_len
            padded_attention_masks.append(padded_mask)

            # Pad labels with IGNORE_INDEX (-100)
            if padded_labels is not None and "labels" in f:
                raw_labels = f["labels"][:batch_max]
                pad_lab = raw_labels + [self.label_pad_token_id] * pad_len
                padded_labels.append(pad_lab)

        return Batch(
            input_ids=padded_input_ids,
            attention_mask=padded_attention_masks,
            labels=padded_labels,
        )


class TrainingDataLoader:
    """Deterministic, seed-shuffled data loader for agent training batches."""

    def __init__(
        self,
        features: List[Dict[str, List[int]]],
        batch_size: int = 4,
        shuffle: bool = True,
        seed: int = 42,
        collator: Optional[DataCollatorForCausalLM] = None,
        tokenizer: Optional[BaseTokenizer] = None,
    ) -> None:
        self.features = features
        self.batch_size = max(1, batch_size)
        self.shuffle = shuffle
        self.seed = seed
        self._epoch = 0

        if collator is not None:
            self.collator = collator
        else:
            tok = tokenizer or XerenTokenizer()
            self.collator = DataCollatorForCausalLM(pad_token_id=tok.pad_token_id)

    def set_epoch(self, epoch: int) -> None:
        """Set epoch to ensure reproducible yet distinct shuffling per epoch."""
        self._epoch = epoch

    def __len__(self) -> int:
        return (len(self.features) + self.batch_size - 1) // self.batch_size

    def __iter__(self) -> Iterator[Batch]:
        indices = list(range(len(self.features)))
        if self.shuffle:
            rng = random.Random(self.seed + self._epoch)
            rng.shuffle(indices)

        for i in range(0, len(indices), self.batch_size):
            batch_indices = indices[i : i + self.batch_size]
            batch_features = [self.features[idx] for idx in batch_indices]
            yield self.collator.collate(batch_features)
