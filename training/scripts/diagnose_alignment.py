#!/usr/bin/env python3
"""
Deep Diagnostic & Comparison Script for Xeren 214M:
Stage-1 (Base) vs Stage-1 Matured Checkpoints
"""

import os
import sys
import json
import math
import torch
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from training.src.model.xeren_transformer import XerenTransformer, XerenConfig
from training.src.tokenizer.train_tokenizer import XerenTokenizer

STAGE1_CKPT = REPO_ROOT / "training" / "checkpoints" / "stage1" / "checkpoint_final.pt"
MATURED_CKPT = REPO_ROOT / "training" / "checkpoints" / "stage1_matured" / "checkpoint_final.pt"
TOKENIZER_DIR = REPO_ROOT / "training" / "checkpoints" / "tokenizer_32k"
VAL_DATA_PATH = REPO_ROOT / "training" / "data" / "processed" / "matured_alignment_val.json"
TRAIN_DATA_PATH = REPO_ROOT / "training" / "data" / "processed" / "matured_alignment_train.json"

BENCHMARK_PROMPTS = [
    {
        "category": "Xeren Identity & Architecture",
        "prompt": "What is Xeren and what are the core components of your architecture?",
        "expected_keywords": ["Xeren", "architecture", "Router", "RAG", "tools", "verification", "memory"]
    },
    {
        "category": "General Knowledge & Conversation",
        "prompt": "What is the capital of France and what is it famous for?",
        "expected_keywords": ["Paris", "France", "Eiffel Tower", "art", "culture", "Louvre"]
    },
    {
        "category": "Arithmetic Reasoning",
        "prompt": "What is 45 + 78? Show your step-by-step calculation.",
        "expected_keywords": ["123", "45", "78"]
    },
    {
        "category": "Python Programming",
        "prompt": "Write a Python function to reverse a string and explain how it works.",
        "expected_keywords": ["def", "reverse", "return", "[::-1]"]
    },
    {
        "category": "RAG & Retrieval Architecture",
        "prompt": "How does the RAG pipeline in Xeren index documents and retrieve relevant chunks?",
        "expected_keywords": ["chunks", "embedding", "vector", "retrieve", "BM25", "reranking"]
    },
    {
        "category": "Tool Usage & JSON Dispatch",
        "prompt": "Dispatch a JSON tool call to list all files in the directory 'training/src'.",
        "expected_keywords": ["tool", "parameters", "directory", "training/src"]
    },
    {
        "category": "Agent Multi-Step Planning",
        "prompt": "Provide a numbered execution plan to inspect, test, and deploy a Python package.",
        "expected_keywords": ["1", "2", "3", "test", "deploy"]
    },
    {
        "category": "Security & Verification",
        "prompt": "How does Xeren ensure safe execution of code and prevent malicious actions?",
        "expected_keywords": ["sandbox", "verification", "security", "threat", "ast", "safe"]
    }
]

def load_model(ckpt_path: Path, device: str = "cuda") -> Tuple[XerenTransformer, Dict[str, Any]]:
    print(f"Loading checkpoint: {ckpt_path}")
    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)
    cfg_dict = checkpoint.get("config", {})
    
    # Handle XerenConfig reconstruction
    if isinstance(cfg_dict, dict):
        model_kwargs = {
            "vocab_size": cfg_dict.get("vocab_size", 32768),
            "dim": cfg_dict.get("dim", cfg_dict.get("hidden_dim", 1024)),
            "n_layers": cfg_dict.get("n_layers", cfg_dict.get("num_layers", 16)),
            "n_heads": cfg_dict.get("n_heads", cfg_dict.get("num_heads", 16)),
            "n_kv_heads": cfg_dict.get("n_kv_heads", cfg_dict.get("num_kv_heads", 4)),
            "hidden_dim": cfg_dict.get("intermediate_dim", cfg_dict.get("hidden_dim_swiglu", 2816)),
            "max_seq_len": cfg_dict.get("max_seq_len", 2048),
            "tie_word_embeddings": cfg_dict.get("tie_word_embeddings", True),
        }
        config = XerenConfig(**model_kwargs)
    elif isinstance(cfg_dict, XerenConfig):
        config = cfg_dict
    else:
        config = XerenConfig(vocab_size=32768, dim=1024, n_layers=16, n_heads=16, n_kv_heads=4, hidden_dim=2816, max_seq_len=2048)

    model = XerenTransformer(config).to(device)
    state_dict = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict)
    model.eval()
    return model, checkpoint

def compute_val_loss_and_perplexity(model: XerenTransformer, tokenizer: XerenTokenizer, val_path: Path, device: str = "cuda") -> Dict[str, float]:
    with open(val_path, "r", encoding="utf-8") as f:
        val_data = json.load(f)
    
    pad_id = tokenizer.pad_token_id or 0
    im_start_id = tokenizer._tokenizer.token_to_id("<|im_start|>")
    im_end_id = tokenizer._tokenizer.token_to_id("<|im_end|>")
    
    total_loss_masked = 0.0
    total_tokens_masked = 0
    
    total_loss_all = 0.0
    total_tokens_all = 0
    
    with torch.no_grad():
        for sample in val_data:
            if isinstance(sample, str):
                formatted = sample
            else:
                messages = sample.get("messages", [])
                formatted = ""
                for msg in messages:
                    role = msg["role"]
                    content = msg["content"]
                    formatted += f"<|im_start|>{role}\n{content}<|im_end|>\n"
            
            tokens = tokenizer.encode(formatted, add_special_tokens=True)
            if len(tokens) > 2048:
                tokens = tokens[:2048]
            
            input_ids = torch.tensor([tokens[:-1]], dtype=torch.long, device=device)
            target_ids = torch.tensor([tokens[1:]], dtype=torch.long, device=device)
            
            labels_masked = target_ids.clone()
            
            is_assistant = [False] * len(tokens)
            in_assistant = False
            
            i = 0
            while i < len(tokens):
                if tokens[i] == im_start_id:
                    role_sub = tokens[i+1:i+4]
                    decoded_role = tokenizer.decode(role_sub)
                    if "assistant" in decoded_role:
                        in_assistant = True
                    else:
                        in_assistant = False
                elif tokens[i] == im_end_id:
                    if in_assistant:
                        is_assistant[i] = True
                        in_assistant = False
                if in_assistant:
                    is_assistant[i] = True
                i += 1
            
            target_mask = torch.tensor([is_assistant[1:]], dtype=torch.bool, device=device)
            labels_masked[~target_mask] = -100
            
            out = model(input_ids)
            logits = out["logits"]
            
            if (labels_masked != -100).sum() > 0:
                loss_m = F.cross_entropy(logits.view(-1, logits.size(-1)), labels_masked.view(-1), ignore_index=-100, reduction='sum')
                num_m = (labels_masked != -100).sum().item()
                total_loss_masked += loss_m.item()
                total_tokens_masked += num_m
            
            loss_a = F.cross_entropy(logits.view(-1, logits.size(-1)), target_ids.view(-1), reduction='sum')
            total_loss_all += loss_a.item()
            total_tokens_all += target_ids.numel()
            
    avg_loss_masked = total_loss_masked / max(total_tokens_masked, 1)
    ppl_masked = math.exp(min(avg_loss_masked, 50.0))
    
    avg_loss_all = total_loss_all / max(total_tokens_all, 1)
    ppl_all = math.exp(min(avg_loss_all, 50.0))
    
    return {
        "val_loss_assistant_masked": avg_loss_masked,
        "val_ppl_assistant_masked": ppl_masked,
        "val_loss_all_tokens": avg_loss_all,
        "val_ppl_all_tokens": ppl_all,
        "assistant_tokens_evaluated": total_tokens_masked,
        "all_tokens_evaluated": total_tokens_all
    }

def generate_response(model: XerenTransformer, tokenizer: XerenTokenizer, prompt: str, device: str = "cuda") -> str:
    system_prompt = "You are Xeren, a specialized and secure autonomous AI agent."
    chatml_input = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    
    input_ids = torch.tensor([tokenizer.encode(chatml_input, add_special_tokens=True)], dtype=torch.long, device=device)
    
    eos_id = tokenizer.eos_token_id or tokenizer._tokenizer.token_to_id("<|im_end|>")
    im_end_id = tokenizer._tokenizer.token_to_id("<|im_end|>")
    
    generated = input_ids[0].tolist()
    max_new_tokens = 150
    temperature = 0.2
    repetition_penalty = 1.2
    
    with torch.no_grad():
        for _ in range(max_new_tokens):
            curr_input = torch.tensor([generated], dtype=torch.long, device=device)
            if curr_input.shape[1] > 2048:
                curr_input = curr_input[:, -2048:]
            
            logits = model(curr_input)["logits"][:, -1, :]
            
            for prev_token in set(generated[input_ids.shape[1]:]):
                if logits[0, prev_token] > 0:
                    logits[0, prev_token] /= repetition_penalty
                else:
                    logits[0, prev_token] *= repetition_penalty
                    
            if temperature > 0:
                probs = F.softmax(logits / temperature, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1).item()
            else:
                next_token = torch.argmax(logits, dim=-1).item()
                
            if next_token in (eos_id, im_end_id):
                break
                
            generated.append(next_token)
            
    response_tokens = generated[input_ids.shape[1]:]
    return tokenizer.decode(response_tokens).strip()

def check_dataset_near_duplicates(prompts: List[Dict[str, Any]], dataset_path: Path) -> List[Dict[str, Any]]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    results = []
    for item in prompts:
        p_text = item["prompt"].lower()
        matches = []
        for sample in data:
            u_text = ""
            if isinstance(sample, str):
                # extract user content from chatml string
                if "<|im_start|>user\n" in sample:
                    u_part = sample.split("<|im_start|>user\n")[1].split("<|im_end|>")[0]
                    u_text = u_part.lower()
            else:
                messages = sample.get("messages", [])
                for m in messages:
                    if m["role"] == "user":
                        u_text = m["content"].lower()
            
            if u_text:
                p_words = set(p_text.split())
                u_words = set(u_text.split())
                jaccard = len(p_words & u_words) / max(len(p_words | u_words), 1)
                if jaccard > 0.35 or p_text in u_text or u_text in p_text:
                    matches.append({
                        "user_text": u_text.strip(),
                        "jaccard": round(jaccard, 3),
                    })
        results.append({
            "category": item["category"],
            "prompt": item["prompt"],
            "matches_found": len(matches),
            "top_matches": sorted(matches, key=lambda x: x["jaccard"], reverse=True)[:3]
        })
    return results

def main():
    print("=" * 80)
    print("XEREN 214M COMPREHENSIVE ALIGNMENT & ARCHITECTURE DIAGNOSTIC")
    print("=" * 80)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    
    # 1. Tokenizer Inspection
    print("\n--- [1] Tokenizer & Special Tokens Inspection ---")
    tokenizer = XerenTokenizer.load(str(TOKENIZER_DIR))
    print(f"Vocab size: {tokenizer.vocab_size}")
    special_tokens = {
        "bos": (tokenizer.bos_token, tokenizer.bos_token_id),
        "eos": (tokenizer.eos_token, tokenizer.eos_token_id),
        "pad": (tokenizer.pad_token, tokenizer.pad_token_id),
        "unk": (tokenizer.unk_token, tokenizer.unk_token_id),
        "<|im_start|>": ("<|im_start|>", tokenizer._tokenizer.token_to_id("<|im_start|>")),
        "<|im_end|>": ("<|im_end|>", tokenizer._tokenizer.token_to_id("<|im_end|>")),
        "assistant": ("assistant", tokenizer._tokenizer.token_to_id("assistant")),
        "user": ("user", tokenizer._tokenizer.token_to_id("user")),
        "system": ("system", tokenizer._tokenizer.token_to_id("system")),
    }
    for k, (tok, tid) in special_tokens.items():
        print(f"  Token: {k:15s} -> ID: {tid}")
        
    sample_text = "<|im_start|>system\nYou are Xeren.<|im_end|>\n<|im_start|>user\nHi<|im_end|>\n<|im_start|>assistant\n"
    enc = tokenizer.encode(sample_text, add_special_tokens=True)
    dec = tokenizer.decode(enc)
    print(f"\nSample ChatML Encode/Decode test:")
    print(f"  Input Tokens ({len(enc)}): {enc[:12]}...")
    print(f"  Decoded: {repr(dec)}")
    print(f"  Starts with BOS? {enc[0] == tokenizer.bos_token_id} (ID: {enc[0]})")
    
    # 2. Checkpoint Inspection
    print("\n--- [2] Checkpoint Config & Structure Inspection ---")
    model_s1, ckpt_s1 = load_model(STAGE1_CKPT, device=device)
    
    # 3. Validation Loss & Perplexity on Stage 1
    print("\n--- [3] Stage 1 Base Metrics ---")
    metrics_s1 = compute_val_loss_and_perplexity(model_s1, tokenizer, VAL_DATA_PATH, device=device)
    for k, v in metrics_s1.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
        
    # Unload model_s1 from CUDA to save VRAM
    del model_s1
    del ckpt_s1
    torch.cuda.empty_cache()
    
    # Load Matured
    model_mat, ckpt_mat = load_model(MATURED_CKPT, device=device)
    print("\n--- [4] Matured Checkpoint Metrics ---")
    metrics_mat = compute_val_loss_and_perplexity(model_mat, tokenizer, VAL_DATA_PATH, device=device)
    for k, v in metrics_mat.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
        
    # 4. Reload Model 1 on CPU or GPU for side-by-side generation
    print("\n--- [5] Side-by-Side 8 Benchmark Evaluation ---")
    model_s1, ckpt_s1 = load_model(STAGE1_CKPT, device=device)
    benchmark_outputs = []
    
    for i, b in enumerate(BENCHMARK_PROMPTS, 1):
        prompt = b["prompt"]
        cat = b["category"]
        print(f"\n[{i}/8] Category: {cat}")
        print(f"Prompt: {prompt}")
        
        # Stage 1 Generation
        resp_s1 = generate_response(model_s1, tokenizer, prompt, device=device)
        # Matured Generation
        resp_mat = generate_response(model_mat, tokenizer, prompt, device=device)
        
        print(f"Stage 1 Output : {resp_s1[:120]}...")
        print(f"Matured Output : {resp_mat[:120]}...")
        
        benchmark_outputs.append({
            "category": cat,
            "prompt": prompt,
            "stage1_response": resp_s1,
            "matured_response": resp_mat,
            "expected_keywords": b["expected_keywords"],
        })
        
    # 5. Dataset Duplication & Near-Matches Check
    print("\n--- [6] Training Dataset Overlap Analysis ---")
    train_overlap = check_dataset_near_duplicates(BENCHMARK_PROMPTS, TRAIN_DATA_PATH)
    val_overlap = check_dataset_near_duplicates(BENCHMARK_PROMPTS, VAL_DATA_PATH)
    
    # 6. Save Diagnostic JSON
    diag_report = {
        "tokenizer_info": {k: {"token": tok, "id": tid} for k, (tok, tid) in special_tokens.items()},
        "stage1_val_metrics": metrics_s1,
        "matured_val_metrics": metrics_mat,
        "benchmark_comparisons": benchmark_outputs,
        "train_prompt_overlap": train_overlap,
        "val_prompt_overlap": val_overlap
    }
    
    out_json = REPO_ROOT / "training" / "checkpoints" / "stage1_matured" / "diagnostic_comparison.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(diag_report, f, indent=2)
    print(f"\n[OK] Diagnostic report saved to: {out_json}")

if __name__ == "__main__":
    main()
