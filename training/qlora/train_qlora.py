"""Xeren QLoRA Fine-Tuning Script.

Fine-tunes TinyLlama-1.1B-Chat on Xeren's agent behavior using QLoRA:
  - 4-bit NF4 quantization (bitsandbytes) — 1.1B model uses only ~700MB VRAM
  - LoRA adapters on all attention + FFN projections (~6.7M trainable params)
  - paged AdamW 8-bit optimizer — prevents VRAM spikes
  - Target GPU: RTX A1000 4-6GB  |  Expected time: 4-6 hours

Run:
  python training/qlora/train_qlora.py
"""

import json
import sys
import os
from pathlib import Path

import yaml
import torch

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

# ── HuggingFace / PEFT / TRL ──────────────────────────────────────────────────
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
from datasets import Dataset


# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path("training/qlora/qlora_config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ── Dataset ───────────────────────────────────────────────────────────────────
def load_xeren_dataset(cfg: dict):
    """Load Xeren ChatML training data and convert to TinyLlama format."""
    train_path = Path(cfg["data"]["train_file"])
    val_path = Path(cfg["data"]["val_file"])

    with open(train_path, "r", encoding="utf-8") as f:
        train_texts = json.load(f)
    with open(val_path, "r", encoding="utf-8") as f:
        val_texts = json.load(f)

    # TinyLlama-1.1B-Chat uses the same ChatML format (<|im_start|> / <|im_end|>)
    # Our data is already in this format — pass through directly.
    def make_dataset(texts):
        return Dataset.from_dict({"text": texts})

    train_ds = make_dataset(train_texts)
    val_ds = make_dataset(val_texts)

    print(f"  • Train samples : {len(train_ds)}")
    print(f"  • Val   samples : {len(val_ds)}")
    return train_ds, val_ds


# ── Model ─────────────────────────────────────────────────────────────────────
def load_quantized_model(cfg: dict):
    """Load TinyLlama in 4-bit NF4 quantization."""
    qcfg = cfg["quantization"]
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=qcfg["load_in_4bit"],
        bnb_4bit_quant_type=qcfg["bnb_4bit_quant_type"],
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=qcfg["bnb_4bit_use_double_quant"],
    )

    model_name = cfg["base_model"]["name"]
    print(f"  Loading base model: {model_name}")
    print(f"  Quantization: 4-bit NF4 + double quant")

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=cfg["base_model"]["trust_remote_code"],
    )
    model.config.use_cache = False          # Required for gradient checkpointing
    model.config.pretraining_tp = 1

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=cfg["base_model"]["trust_remote_code"],
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"        # Required for SFTTrainer

    return model, tokenizer


# ── LoRA ──────────────────────────────────────────────────────────────────────
def apply_lora(model, cfg: dict):
    """Wrap model with LoRA adapters via PEFT."""
    lcfg = cfg["lora"]
    lora_config = LoraConfig(
        r=lcfg["r"],
        lora_alpha=lcfg["lora_alpha"],
        lora_dropout=lcfg["lora_dropout"],
        bias=lcfg["bias"],
        task_type=TaskType.CAUSAL_LM,
        target_modules=lcfg["target_modules"],
    )

    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)

    trainable, total = model.get_nb_trainable_parameters()
    print(f"  Trainable params : {trainable:,}  ({100 * trainable / total:.2f}% of {total:,})")
    return model


# ── Training ──────────────────────────────────────────────────────────────────
def train(cfg: dict, model, tokenizer, train_ds, val_ds):
    tcfg = cfg["training"]

    training_args = TrainingArguments(
        output_dir=tcfg["output_dir"],
        num_train_epochs=tcfg["num_train_epochs"],
        per_device_train_batch_size=tcfg["per_device_train_batch_size"],
        gradient_accumulation_steps=tcfg["gradient_accumulation_steps"],
        learning_rate=tcfg["learning_rate"],
        lr_scheduler_type=tcfg["lr_scheduler_type"],
        warmup_ratio=tcfg["warmup_ratio"],
        weight_decay=tcfg["weight_decay"],
        max_grad_norm=tcfg["max_grad_norm"],
        logging_steps=tcfg["logging_steps"],
        save_steps=tcfg["save_steps"],
        eval_steps=tcfg["eval_steps"],
        evaluation_strategy="steps",
        save_total_limit=tcfg["save_total_limit"],
        fp16=tcfg["fp16"],
        optim=tcfg["optim"],
        dataloader_num_workers=tcfg["dataloader_num_workers"],
        report_to="none",                   # No wandb/tensorboard required
        load_best_model_at_end=True,
        group_by_length=True,               # Speeds up training by grouping similar-length sequences
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=tcfg["max_seq_length"],
        packing=False,
    )

    print("\n  Starting QLoRA fine-tuning...")
    trainer.train()

    # Save LoRA adapter weights
    adapter_dir = Path(tcfg["output_dir"]) / "adapter_final"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    print(f"\n  ✓ LoRA adapter saved to: {adapter_dir}")
    return adapter_dir


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  XEREN QLoRA FINE-TUNING  |  TinyLlama-1.1B-Chat")
    print("=" * 60)

    # GPU check
    if not torch.cuda.is_available():
        print("ERROR: No CUDA GPU detected. QLoRA requires a CUDA GPU.")
        print("       Run on your RTX A1000 or a cloud GPU.")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    print(f"\n✓ GPU : {gpu_name}  ({vram_gb:.1f} GB VRAM)")

    if vram_gb < 4:
        print("WARNING: Less than 4GB VRAM detected. Training may OOM.")

    cfg = load_config()

    print("\n[1/4] Loading dataset...")
    train_ds, val_ds = load_xeren_dataset(cfg)

    print("\n[2/4] Loading quantized base model...")
    model, tokenizer = load_quantized_model(cfg)

    print("\n[3/4] Applying LoRA adapters...")
    model = apply_lora(model, cfg)

    print("\n[4/4] Training...")
    adapter_dir = train(cfg, model, tokenizer, train_ds, val_ds)

    print("\n" + "=" * 60)
    print("✓ QLoRA Fine-Tuning Complete!")
    print(f"  Adapter saved to : {adapter_dir}")
    print(f"  Serve with       : python training/qlora/serve_qlora.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
