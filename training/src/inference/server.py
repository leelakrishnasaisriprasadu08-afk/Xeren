"""OpenAI-compatible HTTP API server for serving Xeren LLM."""

import json
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

import sys
from pathlib import Path

# Add project root
root_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from training.src.inference.generate import XerenGenerator
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer

app = FastAPI(title="Xeren LLM Inference Server")

# Global generator instance
_generator: Optional[XerenGenerator] = None
_model_id: str = "xeren-scratch-v1"


class ChatMessageRequest(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "xeren-scratch-v1"
    messages: List[ChatMessageRequest]
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 256
    stream: bool = False


@app.get("/health")
def health_check():
    return {"status": "healthy", "model": _model_id}


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": _model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "xeren",
            }
        ],
    }


@app.post("/v1/chat/completions")
def create_chat_completion(request: ChatCompletionRequest):
    global _generator
    if _generator is None:
        raise HTTPException(status_code=503, detail="Model is not initialized on server.")

    # Format messages into ChatML prompt
    messages_dicts = [{"role": m.role, "content": m.content} for m in request.messages]
    prompt = _generator.tokenizer.format_chat(messages_dicts)
    # Add assistant trigger
    prompt += "<|im_start|>assistant\n"

    completion_text = _generator.generate(
        prompt=prompt,
        max_new_tokens=request.max_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
    )

    # Clean response (extract assistant text before end token)
    if "<|im_start|>assistant\n" in completion_text:
        completion_text = completion_text.split("<|im_start|>assistant\n")[-1]
    if "<|im_end|>" in completion_text:
        completion_text = completion_text.split("<|im_end|>")[0].strip()

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": completion_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(_generator.tokenizer.encode(prompt)),
            "completion_tokens": len(_generator.tokenizer.encode(completion_text)),
            "total_tokens": len(_generator.tokenizer.encode(prompt + completion_text)),
        },
    }


def start_server(
    checkpoint_path: str,
    tokenizer_dir: str,
    config_preset: str = "nano",
    host: str = "127.0.0.1",
    port: int = 8000,
    device: str = "cpu",
):
    """Load model & tokenizer and start inference server."""
    global _generator, _model_id

    import torch

    tokenizer = XerenTokenizer.load(tokenizer_dir)
    if config_preset == "nano":
        config = XerenConfig.nano(vocab_size=tokenizer.vocab_size)
    else:
        config = XerenConfig.mini(vocab_size=tokenizer.vocab_size)

    model = XerenTransformer(config)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])

    _generator = XerenGenerator(model, tokenizer, device=device)
    _model_id = f"xeren-{config_preset}"

    print(f"Xeren LLM Inference Server running at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--preset", default="nano", choices=["nano", "mini"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    start_server(
        checkpoint_path=args.checkpoint,
        tokenizer_dir=args.tokenizer,
        config_preset=args.preset,
        port=args.port,
    )
