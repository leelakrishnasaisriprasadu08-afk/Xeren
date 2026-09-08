"""Interactive Terminal Chat with your Scratch-Trained Xeren LLM."""

import json
import sys
from pathlib import Path
import torch

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from training.src.inference.generate import XerenGenerator
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("        TALK TO YOUR SCRATCH-TRAINED XEREN LLM")
    print("=" * 60)

    checkpoint_path = Path("training/checkpoints/nano_cpu/checkpoint_final.pt")
    tokenizer_dir = Path("training/checkpoints/tokenizer")

    if not checkpoint_path.exists():
        print(f"Error: Checkpoint {checkpoint_path} not found.")
        return

    print("Loading model and tokenizer...")
    tokenizer = XerenTokenizer.load(tokenizer_dir)

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    config = XerenConfig(**checkpoint["config"])

    model = XerenTransformer(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    generator = XerenGenerator(model, tokenizer, device="cpu")

    print("\n✓ Xeren is ready! Type your message below.")
    print("• Note: This is the 60-step CPU test model. It learns more fluent language")
    print("  after the multi-epoch training on the College GPU.")
    print("• Type 'exit' or 'quit' to stop.\n")
    print("-" * 60)

    conversation_history = ""

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # Format with Xeren ChatML template
        prompt = (
            conversation_history
            + f"<|im_start|>user\n{user_input}\n<|im_end|>\n<|im_start|>assistant\n"
        )

        print("Xeren: ", end="", flush=True)

        # Stream generation
        response_tokens = []
        for token_str in generator.stream_generate(
            prompt,
            max_new_tokens=64,
            temperature=0.7,
            top_k=40,
            top_p=0.9,
        ):
            if "<|im_end|>" in token_str:
                break
            print(token_str, end="", flush=True)
            response_tokens.append(token_str)

        print()  # Newline
        assistant_reply = "".join(response_tokens).strip()

        # Update history (keep last 2 turns)
        conversation_history += (
            f"<|im_start|>user\n{user_input}\n<|im_end|>\n"
            f"<|im_start|>assistant\n{assistant_reply}\n<|im_end|>\n"
        )


if __name__ == "__main__":
    main()
