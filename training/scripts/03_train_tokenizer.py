"""Script 03: Train Xeren BPE Tokenizer from scratch with special agent tokens."""

import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from training.src.tokenizer.train_tokenizer import SPECIAL_TOKENS, XerenTokenizer


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Step 03: Training Xeren Custom Tokenizer ===")
    data_file = Path("training/data/processed/train_texts.json")
    if not data_file.exists():
        print(f"Error: {data_file} not found. Run 02_build_dataset.py first.")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        texts = json.load(f)

    print(f"Loaded {len(texts)} texts for tokenizer training.")

    # Train tokenizer
    vocab_size = 32768  # ~33k vocab for Xeren-1B model (matches mini_1b preset)
    print(f"Training Byte-Level BPE Tokenizer with vocab_size={vocab_size}...")
    tokenizer = XerenTokenizer.train_from_iterator(iter(texts), vocab_size=vocab_size)

    save_dir = Path("training/checkpoints/tokenizer")
    tokenizer.save(save_dir)
    print(f"✓ Tokenizer saved to: {save_dir}")
    print(f"  • Actual Vocab Size: {tokenizer.vocab_size}")
    print(f"  • BOS Token ID: {tokenizer.bos_token_id}")
    print(f"  • EOS Token ID: {tokenizer.eos_token_id}")
    print(f"  • PAD Token ID: {tokenizer.pad_token_id}")

    # Test round-trip encoding
    test_sample = "<|im_start|>thought\nPlan:\n1. Execute vector search\n<|im_end|>"
    encoded = tokenizer.encode(test_sample)
    decoded = tokenizer.decode(encoded)

    print(f"\nVerification:")
    print(f"  • Test input: {repr(test_sample)}")
    print(f"  • Encoded IDs ({len(encoded)} tokens): {encoded}")
    print(f"  • Decoded: {repr(decoded)}")
    assert "<|im_start|>" in decoded, "Special token preservation failed!"
    print("✓ Tokenizer test passed successfully!")


if __name__ == "__main__":
    main()
