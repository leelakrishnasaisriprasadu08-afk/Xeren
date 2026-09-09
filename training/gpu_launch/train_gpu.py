"""Xeren-Mini Two-Stage GPU Training Entry Point.

Usage:
    python training/gpu_launch/train_gpu.py --stage 1   # Train Stage 1 (70M, 16K vocab)
    python training/gpu_launch/train_gpu.py --stage 2   # Train Stage 2 (120M, 32K vocab)
    python training/gpu_launch/train_gpu.py --stage 2 --build-data   # Rebuild dataset first

Stage 1: Trains from scratch on foundation datasets (~30-50 min on RTX A1000)
Stage 2: Initializes from Stage 1 weights, then trains domain specialization (~90-120 min)
"""

import argparse
import json
import os
import sys
from pathlib import Path
import yaml
import torch
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
load_dotenv(root_dir / ".env")

from training.src.data.dataloader import create_dataloader
from training.src.engine.optimizer import build_optimizer, get_cosine_schedule_with_warmup
from training.src.engine.trainer import XerenTrainer
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer


STAGE_CONFIGS = {
    1: "training/configs/xeren_mini_50_gpu.yaml",
    2: "training/configs/xeren_mini_150_gpu.yaml",
}


def check_gpu():
    """Verify GPU availability and print device info."""
    print("=" * 60)
    print("    XEREN-MINI TWO-STAGE GPU TRAINING SYSTEM")
    print("=" * 60)
    if not torch.cuda.is_available():
        print("WARNING: CUDA not available. Falling back to CPU (slow).")
        return "cpu", False
    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"GPU  : {gpu_name}")
    print(f"VRAM : {vram_gb:.2f} GB")
    print(f"CUDA : {torch.version.cuda}")
    print(f"Torch: {torch.__version__}")
    print("=" * 60)
    return "cuda", True


def build_tokenizer_for_stage(stage: int, cfg: dict, all_texts: list) -> XerenTokenizer:
    """Load or train tokenizer for the given stage."""
    tokenizer_dir = Path(cfg["data"]["tokenizer_dir"])
    target_vocab = cfg["model"]["vocab_size"]

    if tokenizer_dir.exists() and (tokenizer_dir / "tokenizer.json").exists():
        print(f"Loading existing tokenizer from {tokenizer_dir}...")
        tokenizer = XerenTokenizer.load(tokenizer_dir)
        print(f"  Tokenizer vocab size: {tokenizer.vocab_size}")

        if tokenizer.vocab_size < target_vocab:
            print(f"Stage requires {target_vocab} vocab tokenizer (current: {tokenizer.vocab_size}). Training new tokenizer...")
            tokenizer = XerenTokenizer.train_from_iterator(iter(all_texts), vocab_size=target_vocab)
            tokenizer.save(tokenizer_dir)
            print(f"  New {target_vocab} tokenizer saved to {tokenizer_dir}")
    else:
        print(f"Training new tokenizer (vocab_size={target_vocab}) from dataset...")
        tokenizer = XerenTokenizer.train_from_iterator(iter(all_texts), vocab_size=target_vocab)
        tokenizer_dir.mkdir(parents=True, exist_ok=True)
        tokenizer.save(tokenizer_dir)
        print(f"  Tokenizer saved to {tokenizer_dir}")

    return tokenizer


def transfer_stage1_weights(stage2_model: XerenTransformer, stage1_path: str) -> bool:
    """Transfer compatible weights from Stage 1 checkpoint into Stage 2 model.
    
    Compatible layers (same dim, transferred directly):
    - Embedding layers (if same vocab size)
    - Transformer blocks 0-11 (all 12 Stage 1 layers)
    - Output LM head (if same vocab size)
    
    Stage 2-only layers (initialized randomly):
    - Transformer blocks 12-17 (6 new layers)
    - Plugin/Confidence/Threat classification heads
    - Expanded embeddings (if vocab expanded from 16K to 32K)
    """
    stage1_path = Path(stage1_path)
    if not stage1_path.exists():
        print(f"WARNING: Stage 1 checkpoint not found at {stage1_path}. Starting Stage 2 from scratch.")
        return False

    print(f"Loading Stage 1 checkpoint from {stage1_path}...")
    checkpoint = torch.load(stage1_path, map_location="cpu")
    stage1_state = checkpoint.get("model_state_dict", checkpoint)

    stage2_state = stage2_model.state_dict()
    transferred = 0
    skipped = 0

    for key, param in stage1_state.items():
        if key not in stage2_state:
            skipped += 1
            continue
        # Only transfer if shapes match exactly
        if stage2_state[key].shape == param.shape:
            stage2_state[key].copy_(param)
            transferred += 1
        else:
            # Partial transfer for expanded embedding tables (16K → 32K vocab)
            if "tok_embeddings" in key or "output.weight" in key:
                old_size = param.shape[0]
                new_size = stage2_state[key].shape[0]
                if old_size < new_size:
                    stage2_state[key][:old_size].copy_(param)
                    transferred += 1
                    print(f"  Partial transfer: {key} ({old_size} → {new_size} vocab)")
            else:
                skipped += 1

    stage2_model.load_state_dict(stage2_state)
    print(f"Weight transfer complete: {transferred} layers transferred, {skipped} skipped (new Stage 2 layers).")
    return True


def main():
    parser = argparse.ArgumentParser(description="Xeren-Mini Two-Stage GPU Training")
    parser.add_argument("--stage", type=int, choices=[1, 2], default=1, help="Training stage (1 or 2)")
    parser.add_argument("--build-data", action="store_true", help="Rebuild dataset before training")
    parser.add_argument("--config", type=str, default=None, help="Override config file path")
    args = parser.parse_args()

    device, use_amp = check_gpu()
    stage = args.stage

    # 1. Load config
    config_path = Path(args.config or STAGE_CONFIGS[stage])
    print(f"\nLoading Stage {stage} config: {config_path}")
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # 2. Build dataset if requested or missing
    train_file = Path(cfg["data"]["train_file"])
    if args.build_data or not train_file.exists():
        print(f"\nBuilding Stage {stage} dataset...")
        from training.src.data.dataset_builder import DatasetBuilder
        builder = DatasetBuilder()
        if stage == 1:
            data = builder.build_stage1_dataset(
                max_samples_per_hf=cfg["data"].get("max_samples_per_hf", 2000)
            )
        else:
            data = builder.build_stage2_dataset(
                max_samples_per_hf=cfg["data"].get("max_samples_per_hf", 3000)
            )
        all_texts = data["train"] + data["val"]
        print(f"Dataset built: {len(data['train'])} train, {len(data['val'])} val samples.")
    else:
        import json as _json
        with open(train_file, "r", encoding="utf-8") as f:
            train_texts = _json.load(f)
        val_file = Path(cfg["data"]["val_file"])
        val_texts = _json.load(open(val_file, "r", encoding="utf-8")) if val_file.exists() else []
        all_texts = train_texts + val_texts
        print(f"Loaded existing dataset: {len(train_texts)} train, {len(val_texts)} val samples.")

    # 3. Tokenizer
    tokenizer = build_tokenizer_for_stage(stage, cfg, all_texts[:5000])  # Use subset for tokenizer training

    # 4. Reload texts as token IDs
    with open(train_file, "r", encoding="utf-8") as f:
        train_texts = json.load(f)
    val_file = Path(cfg["data"]["val_file"])
    val_texts = json.load(open(val_file, "r", encoding="utf-8")) if val_file.exists() else []

    # 5. Build model
    model_cfg = cfg["model"]
    xeren_cfg = XerenConfig(
        vocab_size=tokenizer.vocab_size,
        dim=model_cfg["dim"],
        n_layers=model_cfg["n_layers"],
        n_heads=model_cfg["n_heads"],
        n_kv_heads=model_cfg["n_kv_heads"],
        hidden_dim=model_cfg.get("hidden_dim"),
        max_seq_len=model_cfg["max_seq_len"],
        norm_eps=float(model_cfg["norm_eps"]),
        rope_theta=float(model_cfg.get("rope_theta", 10000.0)),
        dropout=float(model_cfg.get("dropout", 0.0)),
        tie_word_embeddings=model_cfg.get("tie_word_embeddings", False),
        num_plugins=model_cfg.get("num_plugins", 9),
        enable_plugin_head=model_cfg.get("enable_plugin_head", False),
        enable_confidence_head=model_cfg.get("enable_confidence_head", False),
        enable_threat_head=model_cfg.get("enable_threat_head", False),
        num_threat_classes=model_cfg.get("num_threat_classes", 6),
    )

    print(f"\nInitializing Xeren-Mini Stage {stage} model...")
    model = XerenTransformer(xeren_cfg)
    total_params = model.count_parameters()
    print(f"  Parameters: {total_params:,} ({total_params/1e6:.1f}M)")
    print(f"  Vocab size: {xeren_cfg.vocab_size:,}")
    print(f"  Layers: {xeren_cfg.n_layers} | Heads: {xeren_cfg.n_heads} | KV heads: {xeren_cfg.n_kv_heads}")
    print(f"  Max seq len: {xeren_cfg.max_seq_len} | Hidden dim: {xeren_cfg.hidden_dim}")
    if stage == 2:
        print(f"  Plugin head: {xeren_cfg.enable_plugin_head}")
        print(f"  Confidence head: {xeren_cfg.enable_confidence_head}")
        print(f"  Threat head: {xeren_cfg.enable_threat_head}")

    # 6. Weight transfer from Stage 1 (for Stage 2)
    if stage == 2:
        stage1_ckpt = cfg["data"].get("stage1_checkpoint", "training/checkpoints/stage1/checkpoint_final.pt")
        transfer_stage1_weights(model, stage1_ckpt)

    # 7. DataLoaders
    train_loader = create_dataloader(
        train_texts, tokenizer,
        batch_size=cfg["training"]["batch_size"],
        max_seq_len=cfg["data"]["max_seq_len"],
        shuffle=True,
    )
    val_loader = create_dataloader(
        val_texts, tokenizer,
        batch_size=cfg["training"]["batch_size"],
        max_seq_len=cfg["data"]["max_seq_len"],
        shuffle=False,
    ) if val_texts else None

    # 8. Optimizer & Scheduler
    num_epochs = cfg["training"]["num_epochs"]
    grad_accum = cfg["training"]["gradient_accumulation_steps"]
    steps_per_epoch = len(train_loader) // grad_accum
    total_steps = steps_per_epoch * num_epochs

    optimizer = build_optimizer(
        model,
        learning_rate=float(cfg["training"]["learning_rate"]),
        weight_decay=float(cfg["training"]["weight_decay"]),
    )
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=cfg["training"]["num_warmup_steps"],
        num_training_steps=total_steps,
        min_lr_ratio=float(cfg["training"]["min_lr_ratio"]),
    )

    # 9. Trainer
    import os
    trainer = XerenTrainer(
        model=model,
        train_dataloader=train_loader,
        val_dataloader=val_loader,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        gradient_accumulation_steps=grad_accum,
        checkpoint_dir=cfg["data"]["checkpoint_dir"],
        logging_steps=cfg["training"]["logging_steps"],
        eval_steps=cfg["training"]["eval_steps"],
        save_steps=cfg["training"]["save_steps"],
        use_amp=use_amp and cfg["training"].get("use_amp", True),
        gradient_checkpointing=cfg["training"].get("gradient_checkpointing", False),
        lm_loss_weight=float(cfg["training"].get("lm_loss_weight", 1.0)),
        plugin_loss_weight=float(cfg["training"].get("plugin_loss_weight", 0.3)),
        threat_loss_weight=float(cfg["training"].get("threat_loss_weight", 0.2)),
        enable_continuous_training=cfg["training"].get("enable_continuous_training", False),
        continuous_pull_every_steps=cfg["training"].get("continuous_pull_every_steps", 100),
        continuous_max_episodes=cfg["training"].get("continuous_max_episodes", 100),
        postgres_uri=os.getenv("DATABASE_URL"),
    )

    # 10. Train
    print(f"\nStarting Stage {stage} training: {num_epochs} epochs, {total_steps} total steps...")
    history = trainer.train(num_epochs=num_epochs, stage=stage, tokenizer=tokenizer)

    print("\n" + "=" * 60)
    print(f"Stage {stage} Training Complete!")
    print(f"Final checkpoint: {cfg['data']['checkpoint_dir']}/checkpoint_final.pt")
    if stage == 1:
        print("\nNext step: Run Stage 2 training:")
        print("  python training/gpu_launch/train_gpu.py --stage 2 --build-data")
    else:
        print("\nYour Xeren-Mini-150 model is ready!")
        print("Connect to Xeren core via: src/xeren/models/providers/xeren_native.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
