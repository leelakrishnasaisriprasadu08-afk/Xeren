"""PyTorch Dataset and DataLoader for Xeren LLM training."""

from typing import Dict, List, Optional
import torch
from torch.utils.data import DataLoader, Dataset

from training.src.tokenizer.train_tokenizer import XerenTokenizer


class XerenTextDataset(Dataset):
    """Dataset for causal language modeling from raw text strings."""

    def __init__(
        self,
        texts: List[str],
        tokenizer: XerenTokenizer,
        max_seq_len: int = 512,
    ):
        self.texts = texts
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = self.texts[idx]
        token_ids = self.tokenizer.encode(text, add_special_tokens=True)

        # Append EOS if not present
        if not token_ids or token_ids[-1] != self.tokenizer.eos_token_id:
            token_ids.append(self.tokenizer.eos_token_id)

        # Truncate or pad
        if len(token_ids) > self.max_seq_len:
            token_ids = token_ids[: self.max_seq_len]
        
        seq_len = len(token_ids)
        pad_len = self.max_seq_len - seq_len

        input_ids = token_ids + [self.tokenizer.pad_token_id] * pad_len
        # Ignore padding index in loss calculation using -100
        labels = token_ids + [-100] * pad_len

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
            "attention_mask": torch.tensor([1] * seq_len + [0] * pad_len, dtype=torch.long),
        }


def create_dataloader(
    texts: List[str],
    tokenizer: XerenTokenizer,
    batch_size: int = 4,
    max_seq_len: int = 512,
    shuffle: bool = True,
    num_workers: int = 0,
) -> DataLoader:
    """Create a standard DataLoader for training or evaluation."""
    dataset = XerenTextDataset(texts, tokenizer, max_seq_len=max_seq_len)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        drop_last=len(dataset) > batch_size,
    )
