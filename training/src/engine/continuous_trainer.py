"""Xeren Continuous Trainer — Live fine-tuning from Supabase episodes.

Runs as a background process after Stage 2 training is complete.
Polls Supabase every 5 minutes for new user interaction episodes,
then runs mini fine-tuning steps to keep the model improving.

Usage:
    python training/src/engine/continuous_trainer.py
    python training/src/engine/continuous_trainer.py --dry-run
    python training/src/engine/continuous_trainer.py --poll-interval 300
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("xeren.training.continuous")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

root_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root_dir))


class ContinuousTrainer:
    """Continuously fine-tunes Xeren-Mini on new user interaction episodes from Supabase."""

    def __init__(
        self,
        checkpoint_path: str = "training/checkpoints/stage2/checkpoint_final.pt",
        tokenizer_dir: str = "training/checkpoints/tokenizer_32k",
        poll_interval_seconds: int = 300,          # Check Supabase every 5 minutes
        max_episodes_per_cycle: int = 100,
        min_quality_score: float = 0.7,
        max_steps_per_cycle: int = 50,
        learning_rate: float = 2e-5,
        postgres_uri: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.checkpoint_path = Path(checkpoint_path)
        self.tokenizer_dir = tokenizer_dir
        self.poll_interval = poll_interval_seconds
        self.max_episodes = max_episodes_per_cycle
        self.min_quality = min_quality_score
        self.max_steps = max_steps_per_cycle
        self.learning_rate = learning_rate
        self.postgres_uri = postgres_uri or os.getenv("DATABASE_URL", "")
        self.dry_run = dry_run

        self._model = None
        self._tokenizer = None
        self._optimizer = None
        self._device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
        self._cycle_count = 0
        self._total_episodes_trained = 0

    def _load_checkpoint(self):
        """Load the latest Stage 2 checkpoint."""
        import torch
        from training.src.model.config import XerenConfig
        from training.src.model.xeren_transformer import XerenTransformer
        from training.src.tokenizer.train_tokenizer import XerenTokenizer
        from training.src.engine.optimizer import build_optimizer

        if not self.checkpoint_path.exists():
            logger.error(f"Checkpoint not found: {self.checkpoint_path}")
            logger.error("Train Stage 2 first: python training/gpu_launch/train_gpu.py --stage 2")
            sys.exit(1)

        logger.info(f"Loading checkpoint: {self.checkpoint_path}")
        ckpt = torch.load(self.checkpoint_path, map_location=self._device)

        cfg_dict = ckpt.get("config", {})
        xeren_cfg = XerenConfig(**{k: v for k, v in cfg_dict.items() if k in XerenConfig.__dataclass_fields__})

        self._model = XerenTransformer(xeren_cfg)
        self._model.load_state_dict(ckpt["model_state_dict"])
        self._model.to(self._device)
        self._model.train()

        self._tokenizer = XerenTokenizer.load(self.tokenizer_dir)
        self._optimizer = build_optimizer(self._model, learning_rate=self.learning_rate, weight_decay=0.01)

        if ckpt.get("optimizer_state_dict"):
            try:
                self._optimizer.load_state_dict(ckpt["optimizer_state_dict"])
            except Exception:
                pass  # Optimizer state mismatch is OK for continuous training

        params = self._model.count_parameters()
        logger.info(f"Model loaded: {params/1e6:.1f}M params | device={self._device} | vocab={xeren_cfg.vocab_size}")

    def _save_checkpoint(self):
        """Save the updated checkpoint after a continuous training cycle."""
        import torch
        backup_path = self.checkpoint_path.with_name(f"checkpoint_continuous_{self._cycle_count}.pt")
        state = {
            "model_state_dict": self._model.state_dict(),
            "optimizer_state_dict": self._optimizer.state_dict(),
            "config": self._model.config.__dict__,
            "stage": 2,
            "continuous_cycle": self._cycle_count,
            "total_episodes_trained": self._total_episodes_trained,
        }
        # Overwrite main checkpoint
        torch.save(state, self.checkpoint_path)
        # Save cycle backup every 10 cycles
        if self._cycle_count % 10 == 0:
            torch.save(state, backup_path)
            logger.info(f"Cycle backup saved: {backup_path}")
        logger.info(f"Checkpoint updated: {self.checkpoint_path}")

    def _run_one_cycle(self) -> int:
        """Pull new episodes from Supabase and run mini fine-tuning. Returns episodes trained."""
        from training.src.data.continuous_buffer import HybridContinuousBuffer
        from training.src.data.dataset_builder import format_chatml, SYSTEM_PROMPTS
        import torch

        buffer = HybridContinuousBuffer(postgres_uri=self.postgres_uri)

        # First, flush any unsynced local episodes to Supabase
        flushed = buffer.flush_to_supabase()
        if flushed:
            logger.info(f"Flushed {flushed} local episodes to Supabase before training.")

        # Pull untrained episodes from Supabase
        episodes = buffer.pull_for_training(
            max_episodes=self.max_episodes,
            min_quality_score=self.min_quality,
        )

        if not episodes:
            logger.info("No new episodes to train on this cycle.")
            return 0

        logger.info(f"Cycle {self._cycle_count}: Training on {len(episodes)} fresh user episodes...")

        if self.dry_run:
            logger.info("[DRY RUN] Skipping actual training steps.")
            buffer.mark_trained([ep["episode_id"] for ep in episodes])
            return len(episodes)

        scaler = torch.amp.GradScaler("cuda", enabled=(self._device == "cuda"))
        trained_ids = []
        step = 0

        for ep in episodes:
            if step >= self.max_steps:
                break
            try:
                text = format_chatml(SYSTEM_PROMPTS["default"], [
                    {"role": "user", "content": ep["user"]},
                    {"role": "thought", "content": ep.get("thought", "")},
                    {"role": "assistant", "content": ep["assistant"]},
                ])
                ids = self._tokenizer.encode(text)[:self._model.config.max_seq_len]
                if len(ids) < 4:
                    continue

                input_ids = torch.tensor([ids], dtype=torch.long, device=self._device)
                labels = input_ids.clone()

                self._optimizer.zero_grad()
                with torch.amp.autocast("cuda", enabled=(self._device == "cuda")):
                    out = self._model(input_ids, labels=labels)
                    loss = out.get("total_loss") or out.get("loss")
                    if loss is None:
                        continue

                if self._device == "cuda":
                    scaler.scale(loss).backward()
                    scaler.unscale_(self._optimizer)
                    torch.nn.utils.clip_grad_norm_(self._model.parameters(), 1.0)
                    scaler.step(self._optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self._model.parameters(), 1.0)
                    self._optimizer.step()

                trained_ids.append(ep["episode_id"])
                step += 1

                if step % 10 == 0:
                    logger.info(f"  Step {step}/{min(self.max_steps, len(episodes))} | Loss: {loss.item():.4f}")

            except Exception as e:
                logger.warning(f"  Failed episode {ep.get('episode_id', '?')[:8]}: {e}")

        # Mark as trained in Supabase
        if trained_ids:
            buffer.mark_trained(trained_ids)
            self._total_episodes_trained += len(trained_ids)
            logger.info(f"Cycle {self._cycle_count} complete: {len(trained_ids)} episodes trained (total: {self._total_episodes_trained})")

        return len(trained_ids)

    def run(self):
        """Main continuous training loop. Runs indefinitely."""
        logger.info("=" * 60)
        logger.info("  XEREN CONTINUOUS TRAINER STARTED")
        logger.info(f"  Checkpoint: {self.checkpoint_path}")
        logger.info(f"  Poll interval: {self.poll_interval}s ({self.poll_interval//60} minutes)")
        logger.info(f"  Max episodes/cycle: {self.max_episodes}")
        logger.info(f"  Min quality score: {self.min_quality}")
        logger.info(f"  Dry run: {self.dry_run}")
        logger.info("=" * 60)

        self._load_checkpoint()

        while True:
            self._cycle_count += 1
            logger.info(f"\n--- Continuous Training Cycle {self._cycle_count} ---")

            episodes_trained = self._run_one_cycle()

            if episodes_trained > 0 and not self.dry_run:
                self._save_checkpoint()
                logger.info(f"Model updated with {episodes_trained} new episodes. Checkpoint saved.")

            logger.info(f"Sleeping {self.poll_interval}s until next cycle...")
            time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Xeren Continuous Trainer")
    parser.add_argument("--checkpoint", type=str,
                        default="training/checkpoints/stage2/checkpoint_final.pt")
    parser.add_argument("--tokenizer-dir", type=str,
                        default="training/checkpoints/tokenizer_32k")
    parser.add_argument("--poll-interval", type=int, default=300,
                        help="Seconds between Supabase polls (default: 300 = 5 minutes)")
    parser.add_argument("--max-episodes", type=int, default=100)
    parser.add_argument("--min-quality", type=float, default=0.7)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--dry-run", action="store_true",
                        help="Test without running actual training steps")
    args = parser.parse_args()

    trainer = ContinuousTrainer(
        checkpoint_path=args.checkpoint,
        tokenizer_dir=args.tokenizer_dir,
        poll_interval_seconds=args.poll_interval,
        max_episodes_per_cycle=args.max_episodes,
        min_quality_score=args.min_quality,
        learning_rate=args.lr,
        dry_run=args.dry_run,
    )
    trainer.run()


if __name__ == "__main__":
    main()
