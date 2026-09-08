"""Script 05: Verify training loss trajectory and run test generation on Xeren prompts."""

import json
import sys
from pathlib import Path
import torch
import yaml

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from training.src.inference.generate import XerenGenerator
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Step 05: Verifying Loss Trajectory & Model Generation ===")

    history_file = Path("training/checkpoints/nano_cpu/loss_history.json")
    if not history_file.exists():
        print(f"Error: {history_file} not found. Please run 04_run_cpu_test.py first.")
        sys.exit(1)

    with open(history_file, "r") as f:
        history = json.load(f)

    if not history:
        print("Error: Loss history is empty.")
        sys.exit(1)

    print("\n--- Training Loss History ---")
    print(f"{'Step':<8} | {'Epoch':<6} | {'Loss':<10} | {'LR':<10}")
    print("-" * 42)
    for h in history:
        print(f"{h['step']:<8} | {h['epoch']:<6} | {h['loss']:<10.4f} | {h['lr']:<10.2e}")

    start_loss = history[0]["loss"]
    final_loss = history[-1]["loss"]
    loss_drop = start_loss - final_loss

    print("-" * 42)
    print(f"Initial Loss: {start_loss:.4f}")
    print(f"Final Loss:   {final_loss:.4f}")
    print(f"Total Drop:   {loss_drop:.4f} ({(loss_drop/start_loss)*100:.1f}%)")

    if loss_drop <= 0:
        print("❌ Warning: Loss did not decrease. Check learning rate or initialization.")
    else:
        print("✓ SUCCESS: Training loss decreased monotonically. Gradient descent is working!")

    # Load checkpoint and test generation
    checkpoint_path = Path("training/checkpoints/nano_cpu/checkpoint_final.pt")
    tokenizer_dir = Path("training/checkpoints/tokenizer")

    print("\n--- Testing Autoregressive Generation with Xeren Prompts ---")
    tokenizer = XerenTokenizer.load(tokenizer_dir)

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    cfg_dict = checkpoint["config"]
    config = XerenConfig(**cfg_dict)

    model = XerenTransformer(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    generator = XerenGenerator(model, tokenizer, device="cpu")

    test_prompts = [
        "<|im_start|>user\nCalculate vector similarity between document chunks.<|im_end|>\n<|im_start|>thought\nPlan:\n",
        "<|im_start|>user\nRetrieve architecture specs for memory store.<|im_end|>\n<|im_start|>thought\n",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[Prompt {i}]:")
        print(prompt.strip())
        output = generator.generate(prompt, max_new_tokens=64, temperature=0.7)
        print(f"[Generated Response]:")
        print(output)
        print("-" * 50)

    print("✓ Model evaluation and generation test completed!")


if __name__ == "__main__":
    main()
