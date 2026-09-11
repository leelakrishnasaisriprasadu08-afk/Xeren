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
BLUE = "\033[94m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
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
        dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )
    model.eval()

    num_params = sum(p.numel() for p in model.parameters())
    print(f"{GREEN}[Ready] Xeren-Mini loaded! ({num_params / 1e6:.1f}M params | {device.upper()}){RESET}")

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

    # Ensure background preview server is active on port 8080
    try:
        import socket, threading, http.server, functools
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", 8080)) != 0:
                serve_path = Path("d:/Xeren/workspace/generated_sites").resolve()
                serve_path.mkdir(parents=True, exist_ok=True)
                class _QuietHandler(http.server.SimpleHTTPRequestHandler):
                    def log_message(self, format, *args): pass
                _h = functools.partial(_QuietHandler, directory=str(serve_path))
                _srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8080), _h)
                _t = threading.Thread(target=_srv.serve_forever, daemon=True)
                _t.start()
    except Exception:
        pass

    default_system = (
        "You are Xeren, a powerful, fluent AI assistant built by the Xeren team and Leela Krishna. "
        "You help users with coding, research, file operations, web search, data analysis, "
        "and automated workflows using a plugin system. "
        "you are recognize your Xeren engineering team by the 6 members. they are Leela Krishna, Dinesh Kumar, Pallavi, Manideep, Yaswanth, Guna Bhargav and you are devoloped at Vignan's Lara Institute of Technology and Science, Guntur, India. "
        "You are an all-rounder autonomous AI agent equipped with active live execution plugins: WebsitePlugin (generates full-stack and 3D websites with Three.js, WebGL, and live previews), CodingPlugin (runs and tests code in sandboxes), ResearchPlugin (real-time web search and scraping open-source resources), KnowledgePlugin (local RAG), and File/AutomationPlugin (workspace file operations). "
        "You can build websites, render 3D scenes, execute code, search and scrape online, and manage files. Never refuse user requests by claiming you cannot build websites, render 3D objects, execute code, or search the web—you have specialized plugins to do all of these. "
        "You are always helpful, honest, eloquent, and friendly. "
        "You are Xeren and you never claim to be Alibaba, Qwen, ChatGPT, or any other AI model."
    )
    messages: List[Dict[str, str]] = [{"role": "system", "content": default_system}]

    print(f"\n{BOLD}{CYAN}+--------------------------------------------------------------------------------------+{RESET}")
    print(f"{BOLD}{CYAN}|{RESET}  {BOLD}* XEREN AUTONOMOUS REASONING & PLAN DEMONSTRATION AGENT (v1.0-MINI){RESET}           {BOLD}{CYAN}|{RESET}")
    print(f"{BOLD}{CYAN}|{RESET}  {MAGENTA}Institution  :{RESET} Vignan's Lara Institute of Technology & Science, Guntur, India     {BOLD}{CYAN}|{RESET}")
    print(f"{BOLD}{CYAN}|{RESET}  {GREEN}Engineering  :{RESET} Leela Krishna, Dinesh Kumar, Pallavi,                             {BOLD}{CYAN}|{RESET}")
    print(f"{BOLD}{CYAN}|{RESET}                 Manideep, Yaswanth, Guna Bhargav                                     {BOLD}{CYAN}|{RESET}")
    print(f"{BOLD}{CYAN}|{RESET}  {YELLOW}Neural Engine:{RESET} 1.5B Unified Neural Substrate (Local CUDA Standalone)                 {BOLD}{CYAN}|{RESET}")
    print(f"{BOLD}{CYAN}|{RESET}  {BLUE}Capabilities :{RESET} Conversational AI | Deep Multi-Step Planning | 5 Plugin Agents       {BOLD}{CYAN}|{RESET}")
    print(f"{BOLD}{CYAN}+--------------------------------------------------------------------------------------+{RESET}")
    print("  * Type your message to chat, ask for code, or request step-by-step plans.")
    print("  * Type 'create a website for <topic>' to trigger live 3D web generation.")
    print("  * Type 'clear' to reset chat memory  |  Type 'exit' to quit.\n")

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

        # 2. Check if query is an action request using IntentClassifier or plugin triggers
        is_concrete_action = False
        target_plugin = "general"
        if intent_classifier:
            intent_res = intent_classifier.classify(user_input)
            if intent_res.category == RoutingCategory.ACTION_REQUEST:
                is_concrete_action = True
                target_plugin = intent_res.plugin

        if not is_concrete_action and core:
            lower_in = user_input.lower()
            concrete_keywords = [
                "generate website", "create website", "build website", "make a website",
                "create an site", "create a site", "build a site", "make a site",
                "3d website", "3-d website", "web page", "web app", "landing page", "showroom",
                "3d model", "3d object", "3-d model", "3-d object", "three.js", "threejs",
                "run python", "run code", "execute python", "execute code", "run sandbox",
                "search live web", "search the web", "search online", "scrape"
            ]
            if any(kw in lower_in for kw in concrete_keywords):
                is_concrete_action = True
                target_plugin = "action"

        if is_concrete_action and core:
            print(f"\n{CYAN}⚡ [Xeren Autonomous Agent] Decomposing goal and dispatching specialized {target_plugin.upper()} plugin...{RESET}\n")
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

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else 0.2,
                do_sample=temperature > 0,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )

        new_ids = outputs[0][inputs["input_ids"].shape[1]:]
        assistant_reply = tokenizer.decode(new_ids, skip_special_tokens=True).strip()

        # Intercept capability refusals and auto-switch to active plugins
        refusal_triggers = [
            "cannot create physical",
            "cannot create 3d",
            "cannot create websites",
            "cannot build websites",
            "cannot build",
            "cannot generate 3d",
            "cannot generate websites",
            "exceeds my capabilities",
            "unable to create",
            "as an ai assistant, i cannot",
            "as an ai, i cannot",
            "as an ai, i am unable",
            "i do not have the ability to create",
            "i cannot execute",
            "i cannot run code",
        ]
        is_refusal = any(trig in assistant_reply.lower() for trig in refusal_triggers)
        if is_refusal and core:
            print(f"\n{CYAN}⚡ [Xeren Autonomous Engine] Auto-switching plugins for high-demand task...{RESET}\n")
            try:
                import asyncio
                res = asyncio.run(core.aprocess_request(user_input, verify_outcome=True, record_experience=True))
                setattr(core, "_last_action_result", res)
                recovered_reply = res.get("final_response") or "Task executed successfully across Xeren plugins."
                print(f"{BOLD}{CYAN}Xeren (Autonomous Plugins):{RESET}\n{recovered_reply}\n")
                messages.append({"role": "assistant", "content": recovered_reply})
                continue
            except Exception as e:
                print(f"{YELLOW}[Plugin execution note]: {e}{RESET}")

        print(f"\n{BOLD}{CYAN}Xeren:{RESET} {assistant_reply}\n")
        messages.append({"role": "assistant", "content": assistant_reply})


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
