"""Script 04: Train Xeren-Nano from scratch on Laptop CPU (Smoke-Test)."""

import json
import sys
from pathlib import Path
import yaml
import torch

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from training.src.data.dataloader import create_dataloader
from training.src.engine.optimizer import build_optimizer, get_cosine_schedule_with_warmup
from training.src.engine.trainer import XerenTrainer
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Step 04: Training Xeren-Nano from Scratch on Laptop CPU ===")

    config_path = Path("training/configs/xeren_nano_cpu.yaml")
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # 1. Load Tokenizer
    tokenizer_dir = cfg["data"]["tokenizer_dir"]
    print(f"Loading tokenizer from {tokenizer_dir}...")
    tokenizer = XerenTokenizer.load(tokenizer_dir)

    # 2. Build Model Architecture
    model_cfg = cfg["model"]
    xeren_cfg = XerenConfig(
        vocab_size=tokenizer.vocab_size,
        dim=model_cfg["dim"],
        n_layers=model_cfg["n_layers"],
        n_heads=model_cfg["n_heads"],
        n_kv_heads=model_cfg["n_kv_heads"],
        max_seq_len=model_cfg["max_seq_len"],
        norm_eps=float(model_cfg["norm_eps"]),
        tie_word_embeddings=model_cfg["tie_word_embeddings"],
    )
    print(f"Initializing XerenTransformer from scratch (random weights)...")
    model = XerenTransformer(xeren_cfg)
    total_params = model.count_parameters()
    print(f"✓ Model Initialized: {total_params:,} trainable parameters ({total_params/1e6:.2f}M)")

    # 3. Load Data
    with open("training/data/processed/train_texts.json", "r", encoding="utf-8") as f:
        train_texts = json.load(f)
    with open("training/data/processed/val_texts.json", "r", encoding="utf-8") as f:
        val_texts = json.load(f)

    train_loader = create_dataloader(
        train_texts,
        tokenizer,
        batch_size=cfg["training"]["batch_size"],
        max_seq_len=cfg["data"]["max_seq_len"],
        shuffle=True,
    )
    val_loader = create_dataloader(
        val_texts,
        tokenizer,
        batch_size=cfg["training"]["batch_size"],
        max_seq_len=cfg["data"]["max_seq_len"],
        shuffle=False,
    )

    # 4. Optimizer & Scheduler
    max_steps = cfg["training"]["max_steps"]
    optimizer = build_optimizer(
        model,
        learning_rate=float(cfg["training"]["learning_rate"]),
        weight_decay=float(cfg["training"]["weight_decay"]),
    )
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=cfg["training"]["num_warmup_steps"],
        num_training_steps=max_steps,
        min_lr_ratio=float(cfg["training"]["min_lr_ratio"]),
    )

    # 5. Run Trainer
    trainer = XerenTrainer(
        model=model,
        train_dataloader=train_loader,
        val_dataloader=val_loader,
        optimizer=optimizer,
        scheduler=scheduler,
        device=cfg["training"]["device"],
        gradient_accumulation_steps=cfg["training"]["gradient_accumulation_steps"],
        checkpoint_dir=cfg["data"]["checkpoint_dir"],
        logging_steps=cfg["training"]["logging_steps"],
        eval_steps=cfg["training"]["eval_steps"],
        save_steps=cfg["training"]["save_steps"],
        use_amp=cfg["training"]["use_amp"],
    )

    history = trainer.train(
        num_epochs=cfg["training"]["num_epochs"],
        max_steps=max_steps,
    )

    print("\n✓ Laptop CPU Training Test Completed Successfully!")
    if history:
        print(f"  • Starting Loss: {history[0]['loss']:.4f}")
        print(f"  • Final Loss:    {history[-1]['loss']:.4f}")
        loss_diff = history[0]["loss"] - history[-1]["loss"]
        print(f"  • Loss Reduction: {loss_diff:.4f}")


if __name__ == "__main__":
    main()
