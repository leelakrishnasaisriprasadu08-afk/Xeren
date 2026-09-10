"""Interactive Terminal Chat with Xeren (Xeren-Mini Foundation & Legacy Checkpoints).

Features:
- Live token-by-token streaming (ChatGPT-like terminal response)
- Multi-turn conversation memory with ChatML formatting
- Automatic detection of HuggingFace merged weights (xeren_mini_final) vs legacy .pt
- In-chat commands: 'clear', 'reset', 'exit', 'quit', 'system <prompt>'
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import torch
import warnings
warnings.filterwarnings("ignore")

# ANSI Color formatting
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def get_default_checkpoint() -> Path:
    """Find the best available trained checkpoint, prioritizing xeren_mini_final."""
    candidates = [
        Path("training/checkpoints/xeren_mini_final"),
        Path("training/checkpoints/stage1_matured/checkpoint_final.pt"),
        Path("training/checkpoints/stage1/checkpoint_final.pt"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

<<<<<<< HEAD
    checkpoint_path = Path("training/checkpoints/mini_gpu/checkpoint_final.pt")
    tokenizer_dir = Path("training/checkpoints/tokenizer")
=======
>>>>>>> c7566abee2529fc5713f04e8fd0a6dba2545914d

def run_hf_chat(model_dir: Path, device: str, temperature: float, max_tokens: int):
    """Run interactive streaming chat using merged HuggingFace model."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer

    print(f"{CYAN}[Loader] Loading Xeren-Mini from {model_dir}...{RESET}")
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
        fix_mistral_regex=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )
    model.eval()

    num_params = sum(p.numel() for p in model.parameters())
    print(f"{GREEN}[Ready] Xeren-Mini loaded! ({num_params / 1e6:.1f}M params | {device.upper()}){RESET}")

<<<<<<< HEAD
    print("\n✓ Xeren is ready! Type your message below.")
    print("• Note: This is the 60-step CPU test model. It learns more fluent language")
    print("• Model: Xeren trained from scratch.")
    print("• Type 'exit' or 'quit' to stop.\n")
    print("-" * 60)
=======
    # Initialize XerenCore with full plugin architecture
    core = None
    intent_classifier = None
    try:
        ROOT_SRC = Path(__file__).resolve().parent.parent.parent / "src"
        if str(ROOT_SRC) not in sys.path:
            sys.path.insert(0, str(ROOT_SRC))
        from xeren.core.runtime import XerenCore
        from xeren.core.intent import IntentClassifier, RoutingCategory
        core = XerenCore(auto_register_defaults=True)
        intent_classifier = IntentClassifier()
        print(f"{GREEN}[XerenCore] Active Work Agent & Plugins initialized:{RESET}")
        print("  • WebsitePlugin     -> 3D HTML/CSS/JS Generation & Live Local Previews")
        print("  • CodingPlugin      -> Sandbox code execution & syntax verification")
        print("  • ResearchPlugin    -> Live web search & claim verification")
        print("  • KnowledgePlugin   -> Local RAG retrieval & vector grounding")
        print("  • File/Automation   -> Sandboxed workspace files & script execution")
    except Exception as e:
        print(f"{YELLOW}[Notice] Core plugin integration skipped: {e}{RESET}")
        core = None
>>>>>>> c7566abee2529fc5713f04e8fd0a6dba2545914d

    default_system = (
        "You are Xeren, an autonomous reasoning and action AI system capable of "
        "multi-step planning, tool execution, retrieval-augmented generation, and precise problem solving."
    )
    messages: List[Dict[str, str]] = [{"role": "system", "content": default_system}]

    print(f"\n{BOLD}{'=' * 65}")
    print(f"      💬 XEREN INTERACTIVE CHAT TERMINAL")
    print(f"{'=' * 65}{RESET}")
    print("  • Type your message and press Enter.")
    print("  • Type 'clear' to reset chat memory.")
    print("  • Type 'exit' or 'quit' to end session.")
    print(f"{BOLD}{'=' * 65}{RESET}\n")

    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Goodbye!{RESET}")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print(f"{YELLOW}Goodbye! Have a productive day.{RESET}")
            break
        if user_input.lower() in ("clear", "reset"):
            messages = [{"role": "system", "content": default_system}]
            if core:
                setattr(core, "_last_action_result", None)
            print(f"{CYAN}[Chat history reset to fresh context.]{RESET}\n")
            continue
        if user_input.lower().startswith("system "):
            new_sys = user_input[7:].strip()
            messages = [{"role": "system", "content": new_sys}]
            print(f"{CYAN}[System prompt updated: '{new_sys}']{RESET}\n")
            continue

        # 1. Check if user is asking for link of previously created website/task
        last_action_res = getattr(core, "_last_action_result", None) if core else None
        if last_action_res and any(w in user_input.lower() for w in ["link", "url", "where is it", "give link", "show link", "show me the link", "open it"]):
            final_resp = str(last_action_res.get("final_response", ""))
            import re
            links = re.findall(r"(http[s]?://\S+|file://\S+)", final_resp)
            if links:
                clean_link = links[0].rstrip(".)'\"")
                assistant_reply = (
                    f"Here is the active preview link for your generated website:\n\n"
                    f"🔗 {clean_link}\n\n"
                    f"You can open this URL directly in your browser to interact with the 3D animated website."
                )
                print(f"\n{BOLD}{CYAN}Xeren:{RESET}\n{assistant_reply}\n")
                messages.append({"role": "user", "content": user_input})
                messages.append({"role": "assistant", "content": assistant_reply})
                continue

        # 2. Check if query is an action / plugin request
        is_action = False
        if core and intent_classifier:
            intent = intent_classifier.classify(user_input)
            if intent.category == RoutingCategory.ACTION_REQUEST or any(k in user_input.lower() for k in ["create", "build", "generate website", "make a website", "run code", "analyze data", "3d animat"]):
                is_action = True

        if is_action and core:
            print(f"\n{CYAN}⚡ [Xeren Plugin Agent] Orchestrating execution via initialized plugins...{RESET}\n")
            try:
                import asyncio
                res = asyncio.run(core.aprocess_request(user_input, verify_outcome=True, record_experience=True))
                setattr(core, "_last_action_result", res)
                assistant_reply = res.get("final_response") or "Action executed successfully."
                print(f"\n{BOLD}{CYAN}Xeren:{RESET}\n{assistant_reply}\n")
                messages.append({"role": "user", "content": user_input})
                messages.append({"role": "assistant", "content": assistant_reply})
                continue
            except Exception as e:
                print(f"{YELLOW}[Plugin execution note]: {e}{RESET}")

        messages.append({"role": "user", "content": user_input})

        # Apply ChatML template
        if hasattr(tokenizer, "apply_chat_template"):
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            prompt = ""
            for m in messages:
                prompt += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
            prompt += "<|im_start|>assistant\n"

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        print(f"\n{BOLD}{CYAN}Xeren:{RESET} ", end="", flush=True)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                streamer=streamer,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else 0.2,
                do_sample=temperature > 0,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )

        new_ids = outputs[0][inputs["input_ids"].shape[1]:]
        assistant_reply = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        messages.append({"role": "assistant", "content": assistant_reply})
        print()  # Spacer


def run_pt_chat(checkpoint_path: Path, device: str, temperature: float, max_tokens: int):
    """Run legacy chat for scratch .pt checkpoints."""
    from training.src.inference.generate import XerenGenerator
    from training.src.model.config import XerenConfig
    from training.src.model.xeren_transformer import XerenTransformer
    from training.src.tokenizer.train_tokenizer import XerenTokenizer

    tokenizer_path = Path("training/checkpoints/tokenizer_32k")
    if not tokenizer_path.exists():
        tokenizer_path = Path("training/checkpoints/tokenizer")

    print(f"{CYAN}[Loader] Loading legacy .pt checkpoint from {checkpoint_path}...{RESET}")
    tokenizer = XerenTokenizer.load(tokenizer_path)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    config = XerenConfig(**checkpoint.get("config", {}))

    model = XerenTransformer(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    generator = XerenGenerator(model, tokenizer, device=device)
    print(f"{GREEN}[Ready] Legacy model loaded!{RESET}\n")

    system_prompt = "You are Xeren, an autonomous AI assistant."

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Goodbye!{RESET}")
            break

        if not user_input or user_input.lower() in ("exit", "quit"):
            break

        prompt = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n<|im_start|>user\n{user_input}\n<|im_end|>\n<|im_start|>assistant\n"
        print(f"\n{BOLD}{CYAN}Xeren:{RESET} ", end="", flush=True)

        for token_str in generator.stream_generate(prompt, max_new_tokens=max_tokens, temperature=temperature):
            if "<|im_end|>" in token_str or "<|eos|>" in token_str:
                break
            print(token_str, end="", flush=True)
        print("\n")


def main():
    parser = argparse.ArgumentParser(description="Interactive Chat with Xeren")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint directory or .pt file")
    parser.add_argument("--temp", type=float, default=0.3, help="Sampling temperature (0.1 - 0.7)")
    parser.add_argument("--max-tokens", type=int, default=256, help="Max tokens per response")
    parser.add_argument("--device", type=str, default=None, help="cuda or cpu")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint) if args.checkpoint else get_default_checkpoint()
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")

    if not checkpoint_path.exists():
        print(f"{YELLOW}Error: Checkpoint {checkpoint_path} not found.{RESET}")
        return

    # Auto-detect format
    if checkpoint_path.is_dir() and (checkpoint_path / "config.json").exists():
        run_hf_chat(checkpoint_path, device, args.temp, args.max_tokens)
    else:
        run_pt_chat(checkpoint_path, device, args.temp, args.max_tokens)


if __name__ == "__main__":
    main()
