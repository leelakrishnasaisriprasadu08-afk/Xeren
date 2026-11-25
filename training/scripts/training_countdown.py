#!/usr/bin/env python3
"""
Xeren Training Live Countdown & Progress Monitor
=================================================
Displays a real-time countdown showing how much training has completed
and how much time remains. Reads a shared progress file written by the
training script.

Usage:
  # In one terminal — run training:
  python training/scripts/06_train_xeren_mini_qlora.py

  # In another terminal — watch the countdown:
  python training/scripts/training_countdown.py

  # Or specify total expected minutes:
  python training/scripts/training_countdown.py --total_minutes 180
"""

import argparse
import json
import os
import sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import time
from datetime import datetime, timedelta
from pathlib import Path

PROGRESS_FILE = Path("training/checkpoints/xeren_mini_qlora/training_progress.json")

# ANSI
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CLEAR  = "\033[2J\033[H"   # Clear screen + move cursor to top

STAGES = [
    {"name": "📦 Installing & Setup",          "pct_start":  0, "pct_end":  3},
    {"name": "📚 Building Identity Dataset",   "pct_start":  3, "pct_end": 15},
    {"name": "⬇️  Downloading Base Model",      "pct_start": 15, "pct_end": 22},
    {"name": "🔧 Initializing QLoRA Adapters", "pct_start": 22, "pct_end": 25},
    {"name": "🔥 Training — Epoch 1/3",        "pct_start": 25, "pct_end": 50},
    {"name": "🔥 Training — Epoch 2/3",        "pct_start": 50, "pct_end": 75},
    {"name": "🔥 Training — Epoch 3/3",        "pct_start": 75, "pct_end": 92},
    {"name": "🔗 Merging LoRA → Xeren",        "pct_start": 92, "pct_end": 96},
    {"name": "🧪 Running Validation Tests",    "pct_start": 96, "pct_end": 99},
    {"name": "✅ Complete!",                   "pct_start": 99, "pct_end":100},
]


def render_bar(pct: float, width: int = 40) -> str:
    filled = int((pct / 100) * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    if pct >= 100:
        color = GREEN
    elif pct >= 50:
        color = CYAN
    else:
        color = YELLOW
    return f"{color}[{bar}]{RESET} {BOLD}{pct:.1f}%{RESET}"


def get_current_stage(pct: float) -> str:
    for s in STAGES:
        if s["pct_start"] <= pct < s["pct_end"]:
            return s["name"]
    return STAGES[-1]["name"]


def read_progress() -> dict:
    """Read live training progress from the shared JSON file."""
    if not PROGRESS_FILE.exists():
        return {}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def format_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    elif m > 0:
        return f"{m}m {s:02d}s"
    else:
        return f"{s}s"


def countdown_loop(total_minutes: int, refresh_secs: int = 5):
    total_seconds = total_minutes * 60
    start_time = time.time()

    print(f"{CYAN}{BOLD}Xeren Training Monitor started. Refreshing every {refresh_secs}s.{RESET}")
    print(f"  Watching: {PROGRESS_FILE}")
    print(f"  Expected duration: {total_minutes} minutes\n")
    time.sleep(2)

    while True:
        # Read live progress if available
        progress_data = read_progress()
        live_pct      = progress_data.get("percent_complete", None)
        live_loss     = progress_data.get("current_loss", None)
        live_step     = progress_data.get("current_step", None)
        live_total    = progress_data.get("total_steps", None)
        live_epoch    = progress_data.get("current_epoch", None)
        live_status   = progress_data.get("status", "training")
        vram_gb       = progress_data.get("vram_gb", None)
        live_eta_s    = progress_data.get("eta_seconds", None)

        elapsed_s     = time.time() - start_time

        # Fallback: estimate pct from elapsed time if no live file yet
        if live_pct is None:
            time_pct = min((elapsed_s / total_seconds) * 100, 99.0)
            pct = time_pct
            source = "estimated"
        else:
            pct = float(live_pct)
            source = "live"

        # ETA
        if live_eta_s is not None:
            eta_s = float(live_eta_s)
        elif pct > 0:
            eta_s = (elapsed_s / pct) * (100 - pct)
        else:
            eta_s = total_seconds - elapsed_s

        current_stage = get_current_stage(pct)
        now_str = datetime.now().strftime("%H:%M:%S")

        # ── Draw the screen ─────────────────────────────────
        os.system("cls" if os.name == "nt" else "clear")

        print(f"{BOLD}{'═' * 60}{RESET}")
        print(f"{BOLD}{CYAN}   🚀 XEREN-MINI TRAINING — LIVE MONITOR{RESET}")
        print(f"{BOLD}{'═' * 60}{RESET}")
        print()

        # Big progress bar
        print(f"  {render_bar(pct, width=50)}")
        print()

        # Current stage
        print(f"  Stage      : {BOLD}{current_stage}{RESET}")

        # Time info
        print(f"  Elapsed    : {BOLD}{format_duration(elapsed_s)}{RESET}")
        if pct < 100:
            print(f"  ETA        : {BOLD}{YELLOW}{format_duration(eta_s)}{RESET}")
        else:
            print(f"  ETA        : {BOLD}{GREEN}Done!{RESET}")

        print(f"  Clock      : {now_str}  ({source} data)")
        print()

        # Divider
        print(f"  {'─' * 55}")

        # Live training metrics
        if live_step is not None and live_total is not None:
            step_pct = (live_step / live_total) * 100 if live_total > 0 else 0
            print(f"  Step       : {live_step}/{live_total}  ({step_pct:.1f}%)")
        if live_epoch is not None:
            print(f"  Epoch      : {live_epoch}/3")
        if live_loss is not None:
            loss_color = GREEN if float(live_loss) < 1.0 else (YELLOW if float(live_loss) < 2.0 else RED)
            print(f"  Loss       : {loss_color}{BOLD}{live_loss:.4f}{RESET}")
        if vram_gb is not None:
            vram_color = RED if float(vram_gb) > 7.5 else (YELLOW if float(vram_gb) > 6.5 else GREEN)
            print(f"  VRAM Usage : {vram_color}{BOLD}{vram_gb:.2f} GB / 8.00 GB{RESET}")

        print()

        # Stage checklist
        print(f"  {'─' * 55}")
        print(f"  {BOLD}Stages:{RESET}")
        for s in STAGES:
            if pct >= s["pct_end"]:
                mark = f"{GREEN}✅{RESET}"
            elif pct >= s["pct_start"]:
                mark = f"{YELLOW}🔄{RESET}"
            else:
                mark = "⬜"
            print(f"    {mark}  {s['name']}")

        print()
        print(f"{'═' * 60}")

        if pct >= 100 or live_status == "complete":
            print(f"\n  {GREEN}{BOLD}🎉 Training Complete! xeren_mini is ready.{RESET}")
            print(f"  Run: python training/scripts/xeren_mini_validation_tests.py")
            print()
            break

        time.sleep(refresh_secs)


def main():
    parser = argparse.ArgumentParser(description="Xeren Training Live Countdown Monitor")
    parser.add_argument(
        "--total_minutes", type=int, default=180,
        help="Total expected training duration in minutes (default: 180 = 3 hours)"
    )
    parser.add_argument(
        "--refresh", type=int, default=10,
        help="Refresh interval in seconds (default: 10)"
    )
    args = parser.parse_args()
    countdown_loop(total_minutes=args.total_minutes, refresh_secs=args.refresh)


if __name__ == "__main__":
    main()
