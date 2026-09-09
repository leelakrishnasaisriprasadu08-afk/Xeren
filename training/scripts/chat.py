"""Interactive Terminal Chat with your Scratch-Trained Xeren LLM."""

import argparse
import io
import sys
from pathlib import Path
import torch

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from training.src.inference.generate import XerenGenerator
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer


def get_default_checkpoint() -> Path:
    """Find the best available trained checkpoint."""
    candidates = [
        Path("training/checkpoints/stage1_matured/checkpoint_final.pt"),
        Path("training/checkpoints/stage1_matured/checkpoint_pilot.pt"),
        Path("training/checkpoints/stage2/checkpoint_final.pt"),
        Path("training/checkpoints/stage1/checkpoint_final.pt"),
        Path("training/checkpoints/stage1/checkpoint_step_300.pt"),
        Path("training/checkpoints/nano_cpu/checkpoint_final.pt"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[1]


def get_default_tokenizer() -> Path:
    candidates = [
        Path("training/checkpoints/tokenizer_32k"),
        Path("training/checkpoints/tokenizer"),
    ]
    for t in candidates:
        if t.exists() and (t / "tokenizer.json").exists():
            return t
    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description="Talk to your Scratch-Trained Xeren LLM")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint .pt file")
    parser.add_argument("--tokenizer", type=str, default=None, help="Path to tokenizer directory")
    parser.add_argument("--device", type=str, default=None, help="cuda or cpu")
    parser.add_argument("--temp", type=float, default=0.3, help="Sampling temperature")
    parser.add_argument("--repetition-penalty", type=float, default=1.25, help="Repetition penalty")
    parser.add_argument("--max-tokens", type=int, default=100, help="Max response tokens")
    parser.add_argument("--multi-turn", action="store_true", default=False, help="Preserve multi-turn history (default: False, as Stage 1 was trained single-turn)")
    args = parser.parse_args()

    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 65)
    print("         TALK TO YOUR SCRATCH-TRAINED XEREN LLM (TIER 3)")
    print("=" * 65)

    checkpoint_path = Path(args.checkpoint) if args.checkpoint else get_default_checkpoint()
    tokenizer_dir = Path(args.tokenizer) if args.tokenizer else get_default_tokenizer()
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")

    if not checkpoint_path.exists():
        print(f"Error: Checkpoint {checkpoint_path} not found.")
        return

    print(f"Checkpoint : {checkpoint_path}")
    print(f"Tokenizer  : {tokenizer_dir}")
    print(f"Device     : {device.upper()}" + (f" ({torch.cuda.get_device_name(0)})" if device == "cuda" else ""))
    print("Loading model and tokenizer...")

    tokenizer = XerenTokenizer.load(tokenizer_dir)
    checkpoint = torch.load(checkpoint_path, map_location=device)

    config_dict = checkpoint.get("config", {})
    config = XerenConfig(**config_dict)

    model = XerenTransformer(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    generator = XerenGenerator(model, tokenizer, device=device)

    total_params = model.count_parameters()
    print(f"Model Size : {total_params:,} parameters ({total_params/1e6:.1f}M)")
    print(f"Vocab Size : {tokenizer.vocab_size:,} tokens")

    print("\n" + "=" * 65)
    print("✓ Xeren is ready! Type your message below.")
    print("• Commands: 'clear' to reset conversation, 'exit' or 'quit' to stop.")
    print("=" * 65 + "\n")

    system_prompt = (
        "You are Xeren, an autonomous reasoning and action AI system capable of "
        "multi-step planning, tool execution, retrieval-augmented generation, and precise problem solving."
    )
    conversation_history = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"

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
        if user_input.lower() == "clear":
            conversation_history = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"
            print("[Conversation history cleared.]")
            continue

        if args.multi_turn:
            prompt = (
                conversation_history
                + f"<|im_start|>user\n{user_input}\n<|im_end|>\n"
            )
        else:
            prompt = (
                f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"
                f"<|im_start|>user\n{user_input}\n<|im_end|>\n"
            )

        print("\nXeren: ", end="", flush=True)

        full_raw_tokens = []
        started = False
        buffer = ""

        for token_str in generator.stream_generate(
            prompt,
            max_new_tokens=args.max_tokens,
            temperature=args.temp,
            top_k=40,
            top_p=0.9,
            repetition_penalty=args.repetition_penalty,
        ):
            if "<|im_end|>" in token_str or "<|eos|>" in token_str:
                break
            full_raw_tokens.append(token_str)
            buffer += token_str

            if not started:
                # Strip leading tags like <|im_start|>assistant\n
                if "<|im_start|>assistant\n" in buffer:
                    content_start = buffer.split("<|im_start|>assistant\n", 1)[-1]
                    if content_start:
                        print(content_start, end="", flush=True)
                    started = True
                elif len(buffer) > 25 and "<|im_start|>" not in buffer:
                    print(buffer, end="", flush=True)
                    started = True
            else:
                print(token_str, end="", flush=True)

        print()  # Newline
        raw_output = "".join(full_raw_tokens)
        assistant_reply = raw_output.replace("<|im_start|>assistant\n", "").replace("<|im_end|>", "").strip()

        # Update history
        conversation_history += (
            f"<|im_start|>user\n{user_input}\n<|im_end|>\n"
            f"<|im_start|>assistant\n{assistant_reply}\n<|im_end|>\n"
        )


if __name__ == "__main__":
    main()
