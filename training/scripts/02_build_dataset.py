"""Script 02: Build Xeren unified training and validation dataset."""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from training.src.data.dataset_builder import DatasetBuilder


def main():
    print("=== Step 02: Building Multi-Source Xeren Dataset ===")
    builder = DatasetBuilder(output_dir="training/data/processed")

    # For local testing & tokenizer training, max_samples_per_hf=150 is quick and comprehensive
    data = builder.build_stage1_dataset(
        local_train_path="data/train.jsonl",
        local_val_path="data/val.jsonl",
        max_samples_per_hf=150,
    )

    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    print("\n[OK] Dataset Build Finished:")
    print(f"  • Training samples: {len(data['train'])}")
    print(f"  • Validation samples: {len(data['val'])}")
    print(f"  • Files written to: training/data/processed/")


if __name__ == "__main__":
    main()
