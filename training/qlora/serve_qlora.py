"""Xeren QLoRA Inference Server.

Loads the fine-tuned LoRA adapter on top of the 4-bit quantized TinyLlama base
and serves an OpenAI-compatible /v1/chat/completions endpoint.

Run:
  python training/qlora/serve_qlora.py
  python training/qlora/serve_qlora.py --adapter training/checkpoints/qlora_xeren/adapter_final
"""

import sys
import time
import argparse
from pathlib import Path

import torch
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

CONFIG_PATH = Path("training/qlora/qlora_config.yaml")

app = FastAPI(title="Xeren QLoRA Inference Server")

_model = None
_tokenizer = None
_model_id = "xeren-qlora-1b"

SYSTEM_PROMPT = (
    "You are Xeren, an autonomous reasoning and action AI system capable of "
    "multi-step planning, tool execution, retrieval-augmented generation, "
    "and precise problem solving."
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "xeren-qlora-1b"
    messages: List[ChatMessage]
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 256


def load_model(adapter_dir: str, cfg: dict):
    """Load base model in 4-bit + LoRA adapter on top."""
    global _model, _tokenizer

    qcfg = cfg["quantization"]
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=qcfg["load_in_4bit"],
        bnb_4bit_quant_type=qcfg["bnb_4bit_quant_type"],
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=qcfg["bnb_4bit_use_double_quant"],
    )

    base_name = cfg["base_model"]["name"]
    print(f"Loading base model: {base_name} (4-bit)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_name,
        quantization_config=bnb_config,
        device_map="auto",
    )

    print(f"Loading LoRA adapter from: {adapter_dir}")
    _model = PeftModel.from_pretrained(base_model, adapter_dir)
    _model.eval()

    _tokenizer = AutoTokenizer.from_pretrained(adapter_dir)
    _tokenizer.pad_token = _tokenizer.eos_token
    print("✓ Xeren QLoRA model ready.")


def format_prompt(messages: List[ChatMessage]) -> str:
    """Format messages to TinyLlama ChatML format."""
    prompt = ""
    # Ensure system message is first
    has_system = any(m.role == "system" for m in messages)
    if not has_system:
        prompt += f"<|im_start|>system\n{SYSTEM_PROMPT}\n<|im_end|>\n"
    for msg in messages:
        prompt += f"<|im_start|>{msg.role}\n{msg.content}\n<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    return prompt


@app.get("/health")
def health():
    return {"status": "healthy", "model": _model_id}


@app.get("/v1/models")
def models():
    return {
        "object": "list",
        "data": [{"id": _model_id, "object": "model", "owned_by": "xeren"}],
    }


@app.post("/v1/chat/completions")
def chat(request: ChatRequest):
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    prompt = format_prompt(request.messages)
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
    input_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            do_sample=True,
            repetition_penalty=1.15,
            pad_token_id=_tokenizer.eos_token_id,
        )

    generated = outputs[0][input_len:]
    text = _tokenizer.decode(generated, skip_special_tokens=True)
    # Strip trailing stop tokens
    for stop in ["<|im_end|>", "<|im_start|>"]:
        if stop in text:
            text = text.split(stop)[0].strip()

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": input_len,
            "completion_tokens": len(generated),
            "total_tokens": input_len + len(generated),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--adapter",
        default="training/checkpoints/qlora_xeren/adapter_final",
        help="Path to saved LoRA adapter directory",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)

    load_model(args.adapter, cfg)
    print(f"Xeren QLoRA server running at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
