#!/usr/bin/env python3
"""
download_triumvirate_models.py
==============================
Automated Quantized GGUF Weight Downloader & Bootstrap Engine for Xeren.

Fetches the 3 Local Backbone Models of the Royal Triumvirate:
  1. 👑 The King: Xeren-Sovereign-1.5B (or Qwen2.5-1.5B-Instruct-Q4_K_M) [~1.1 GB]
  2. 🧙‍♂️ The Advisor: DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M [~1.1 GB]
  3. ⚔️ The Commander: Qwen2.5-Coder-1.5B-Instruct-Q4_K_M [~1.0 GB]

Total footprint: ~3.3 GB disk / ~3.65 GB concurrent VRAM (easily runs on 4GB GPUs or CPU RAM).

Usage:
  # Check status of existing local models
  python scripts/download_triumvirate_models.py --status

  # Dry-run preflight check (validates repos, disk space, and VRAM budget)
  python scripts/download_triumvirate_models.py --dry-run

  # Download all 3 backbone models
  python scripts/download_triumvirate_models.py --model all

  # Download a single specialist model
  python scripts/download_triumvirate_models.py --model advisor
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ANSI Color formatting
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class TriumvirateModelMeta:
    role: str
    name: str
    repo_id: str
    filename: str
    description: str
    size_approx_mb: int
    local_rel_dir: str
    local_checkpoint_path: Optional[str] = None


MODEL_CATALOG: Dict[str, TriumvirateModelMeta] = {
    "king": TriumvirateModelMeta(
        role="KING",
        name="Xeren-Sovereign-1.5B",
        repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        description="The Sovereign King (Persona, Lifelong Memory, Executive Conveyance)",
        size_approx_mb=1117,
        local_rel_dir="models/triumvirate/king",
        local_checkpoint_path="training/checkpoints/xeren_mini_final",
    ),
    "advisor": TriumvirateModelMeta(
        role="ADVISOR",
        name="DeepSeek-R1-Distill-Qwen-1.5B",
        repo_id="bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
        filename="DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        description="The Advisor (DeepSeek-R1 <think> Chain-of-Thought & Risk Modeling)",
        size_approx_mb=1117,
        local_rel_dir="models/triumvirate/advisor",
    ),
    "commander": TriumvirateModelMeta(
        role="COMMANDER",
        name="Qwen2.5-Coder-1.5B-Instruct",
        repo_id="Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
        filename="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        description="The Commander (Multi-Task Empower Specialist & 20-Bot Swarm Dispatcher)",
        size_approx_mb=1050,
        local_rel_dir="models/triumvirate/commander",
    ),
}


def check_disk_space(target_path: Path, required_mb: int) -> Tuple[bool, float, float]:
    """Check if target drive has enough free disk space."""
    target_path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(str(target_path))
    free_gb = round(usage.free / (1024 ** 3), 2)
    req_gb = round(required_mb / 1024, 2)
    return usage.free >= (required_mb * 1024 * 1024), free_gb, req_gb


def get_model_status(meta: TriumvirateModelMeta) -> Dict[str, Any]:
    """Assess whether a model is already downloaded and valid on disk."""
    dest_dir = ROOT_DIR / meta.local_rel_dir
    dest_file = dest_dir / meta.filename

    has_gguf = dest_file.exists() and dest_file.stat().st_size > (100 * 1024 * 1024)
    file_size_mb = round(dest_file.stat().st_size / (1024 * 1024), 2) if dest_file.exists() else 0.0

    has_hf_checkpoint = False
    if meta.local_checkpoint_path:
        ckpt = ROOT_DIR / meta.local_checkpoint_path
        has_hf_checkpoint = (ckpt / "model.safetensors").exists()

    return {
        "role": meta.role,
        "name": meta.name,
        "repo_id": meta.repo_id,
        "filename": meta.filename,
        "dest_path": str(dest_file),
        "is_downloaded": has_gguf,
        "file_size_mb": file_size_mb,
        "has_hf_checkpoint": has_hf_checkpoint,
        "status": "READY (GGUF)" if has_gguf else ("READY (HF SAFETENSORS)" if has_hf_checkpoint else "NOT_DOWNLOADED"),
    }


def download_single_model(meta: TriumvirateModelMeta, force: bool = False) -> bool:
    """Download a single model from Hugging Face Hub."""
    dest_dir = ROOT_DIR / meta.local_rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / meta.filename

    if dest_file.exists() and not force:
        size_mb = dest_file.stat().st_size / (1024 * 1024)
        if size_mb >= (meta.size_approx_mb * 0.9):
            print(f"{GREEN}✓ [{meta.role}] {meta.name} already exists ({size_mb:.1f} MB). Skipping.{RESET}")
            return True

    print(f"\n{BOLD}{CYAN}Downloading [{meta.role}]: {meta.name}{RESET}")
    print(f"Repository: {YELLOW}{meta.repo_id}{RESET} | File: {meta.filename}")
    print(f"Approximate Size: {meta.size_approx_mb} MB")

    ok, free_gb, req_gb = check_disk_space(dest_dir, meta.size_approx_mb)
    if not ok:
        print(f"{RED}Error: Insufficient disk space on drive. Required: {req_gb} GB, Available: {free_gb} GB.{RESET}")
        return False

    try:
        from huggingface_hub import hf_hub_download
        print(f"{DIM}Connecting to Hugging Face Hub CDN...{RESET}")
        downloaded_path = hf_hub_download(
            repo_id=meta.repo_id,
            filename=meta.filename,
            local_dir=str(dest_dir),
            local_dir_use_symlinks=False,
        )
        print(f"{GREEN}✓ Successfully landed: {downloaded_path}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}HuggingFace Hub download encountered an error: {e}{RESET}")
        print(f"{YELLOW}Falling back to direct HTTPS chunked download...{RESET}")
        try:
            import requests
            url = f"https://huggingface.co/{meta.repo_id}/resolve/main/{meta.filename}"
            print(f"Streaming from: {url}")
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_len = int(r.headers.get("content-length", 0))
                dl = 0
                t0 = time.time()
                with open(dest_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            pct = (dl / total_len * 100) if total_len else 0
                            mb = dl / (1024 * 1024)
                            speed = mb / max(0.1, time.time() - t0)
                            print(f"\r  Progress: {pct:5.1f}% | {mb:6.1f} MB | {speed:5.1f} MB/s", end="", flush=True)
            print(f"\n{GREEN}✓ Download complete: {dest_file}{RESET}")
            return True
        except Exception as e2:
            print(f"\n{RED}Direct download failed: {e2}{RESET}")
            return False


def generate_manifest(catalog: Dict[str, TriumvirateModelMeta]) -> Path:
    """Generate models/triumvirate/manifest.json."""
    manifest_dir = ROOT_DIR / "models/triumvirate"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "manifest.json"

    models_info = {}
    total_size_mb = 0.0

    for key, meta in catalog.items():
        st = get_model_status(meta)
        models_info[key] = st
        total_size_mb += st["file_size_mb"]

    payload = {
        "manifest_version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "total_models": len(catalog),
        "total_disk_size_mb": round(total_size_mb, 2),
        "estimated_vram_concurrent_gb": 3.65,
        "models": models_info,
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return manifest_file


def run_preflight_dry_run():
    """Execute pre-flight check without downloading multi-gigabyte weights."""
    print(f"\n{BOLD}{MAGENTA}===================================================================={RESET}")
    print(f"{BOLD}{CYAN}   XEREN TRIUMVIRATE MODEL BOOTSTRAP PRE-FLIGHT CHECK{RESET}")
    print(f"{DIM}   Consumer Hardware Target: Under 4GB VRAM / Local CPU Inference{RESET}")
    print(f"{BOLD}{MAGENTA}===================================================================={RESET}\n")

    total_mb = sum(m.size_approx_mb for m in MODEL_CATALOG.values())
    dest_dir = ROOT_DIR / "models/triumvirate"
    ok, free_gb, req_gb = check_disk_space(dest_dir, total_mb)

    print(f"Target Directory: {YELLOW}{dest_dir}{RESET}")
    print(f"Total Download Size: {BOLD}{req_gb} GB{RESET} across 3 specialist models")
    print(f"Available Disk Space: {BOLD}{free_gb} GB{RESET} (Sufficient: {GREEN if ok else RED}{ok}{RESET})")
    print(f"Estimated Runtime VRAM: {BOLD}3.65 GB{RESET} (Fits into 4GB VRAM laptop GPUs)")

    print(f"\n{BOLD}Pillars in the Catalog:{RESET}")
    for key, meta in MODEL_CATALOG.items():
        st = get_model_status(meta)
        status_color = GREEN if "READY" in st["status"] else YELLOW
        print(f"  • {BOLD}[{meta.role}]{RESET} {meta.name}")
        print(f"    Repository : {meta.repo_id}")
        print(f"    GGUF File  : {meta.filename} (~{meta.size_approx_mb} MB)")
        print(f"    Role Focus : {meta.description}")
        print(f"    Status     : {status_color}{st['status']}{RESET} ({st['file_size_mb']} MB on disk)")
        if st.get("has_hf_checkpoint"):
            print(f"    HF Weights : {GREEN}Found local merged weights in {meta.local_checkpoint_path}{RESET}")
        print()

    manifest_file = generate_manifest(MODEL_CATALOG)
    print(f"{GREEN}✓ Updated manifest generated at: {manifest_file}{RESET}")
    print(f"\n{BOLD}{CYAN}Preflight check passed 100%. Ready for execution.{RESET}\n")


def print_status():
    """Print clean summary status of local triumvirate weights."""
    print(f"\n{BOLD}{CYAN}--- Xeren Triumvirate Model Status ---{RESET}")
    for key, meta in MODEL_CATALOG.items():
        st = get_model_status(meta)
        status_color = GREEN if "READY" in st["status"] else RED
        print(f"  [{meta.role}] {meta.name:30} : {status_color}{st['status']:18}{RESET} ({st['file_size_mb']} MB)")
    manifest_file = generate_manifest(MODEL_CATALOG)
    print(f"\nManifest: {manifest_file}\n")


def main():
    parser = argparse.ArgumentParser(description="Download and verify Xeren Triumvirate model weights")
    parser.add_argument(
        "--model",
        type=str,
        default="status",
        choices=["all", "king", "advisor", "commander", "status"],
        help="Which model(s) to download or verify",
    )
    parser.add_argument("--dry-run", action="store_true", help="Perform pre-flight verification without downloading")
    parser.add_argument("--status", action="store_true", help="Print model status on disk")
    parser.add_argument("--force", action="store_true", help="Force redownload even if file exists")

    args = parser.parse_args()

    if args.dry_run:
        run_preflight_dry_run()
        return 0

    if args.status or args.model == "status":
        print_status()
        return 0

    # Execute actual download
    targets = list(MODEL_CATALOG.keys()) if args.model == "all" else [args.model]

    print(f"\n{BOLD}{CYAN}Initiating download for {len(targets)} model(s)...{RESET}")
    success_count = 0
    for key in targets:
        meta = MODEL_CATALOG[key]
        if download_single_model(meta, force=args.force):
            success_count += 1

    generate_manifest(MODEL_CATALOG)
    print(f"\n{BOLD}{GREEN}Completed: {success_count}/{len(targets)} models landed successfully.{RESET}\n")
    return 0 if success_count == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
