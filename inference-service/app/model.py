"""Model loader — configurable via MODEL_DIR env var."""

from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import torch

_model = None
_tokenizer = None

def _get_model_dir() -> str:
    """
    Locate the model directory.
    
    Priority:
    1. MODEL_DIR environment variable
    2. Default path /app/models/Qwen3-0.6B (Docker)
    3. Relative path from project root (local dev)
    """
    # Allow override via environment variable
    env_dir = os.environ.get("MODEL_DIR")
    if env_dir and os.path.isdir(env_dir) and os.path.exists(os.path.join(env_dir, "config.json")):
        print(f"Using model from MODEL_DIR: {env_dir}", flush=True)
        return os.path.abspath(env_dir)

    # Default Docker path
    default = "/app/models/default"
    if os.path.isdir(default) and os.path.exists(os.path.join(default, "config.json")):
        print(f"Using model from default path: {default}", flush=True)
        return os.path.abspath(default)

    # Fallback to any model in /app/models/
    models_dir = "/app/models"
    if os.path.isdir(models_dir):
        for entry in os.listdir(models_dir):
            candidate = os.path.join(models_dir, entry)
            if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "config.json")):
                print(f"Using model from: {candidate}", flush=True)
                return os.path.abspath(candidate)

    raise RuntimeError(
        f"No model found. Set MODEL_DIR env var or place model in /app/models/<name>/"
    )

MODEL_DIR = _get_model_dir()

def load_model():
    """Load Qwen3-0.6B into memory. Returns (model, tokenizer)."""
    global _model, _tokenizer
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer

    print(f"Loading model from {MODEL_DIR}...", flush=True)
    _tokenizer = AutoTokenizer.from_pretrained(
        MODEL_DIR, trust_remote_code=True, use_fast=False
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}", flush=True)

    dtype = torch.float16 if device == "cuda" else torch.float32

    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        torch_dtype=dtype,
        device_map=device if device == "cuda" else None,
        trust_remote_code=True,
    )
    if device == "cpu":
        _model = _model.to(device)

    _model.eval()
    print(f"Model loaded successfully on {device}!", flush=True)
    return _model, _tokenizer

def predict(question: str, max_new_tokens: int = 256) -> str:
    """Generate a response for the given question using the loaded model."""
    model, tokenizer = load_model()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": question},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt")

    input_ids = inputs["input_ids"].to(model.device)
    attention_mask = inputs["attention_mask"].to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
        generated_ids = generated_ids[:, input_ids.shape[1]:]

    response = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    return response