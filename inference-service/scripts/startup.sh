#!/usr/bin/env bash
# Startup script for the inference service.
# Downloads the model at runtime (if needed) and starts the FastAPI server.
set -e

MODEL_NAME="${MODEL_NAME:-Qwen3-0.6B}"
HF_REPO_ID="${HF_REPO_ID:-Qwen/Qwen3-0.6B}"
MODEL_DIR="${MODEL_DIR:-/app/models/${MODEL_NAME}}"
HF_ENDPOINT="${HF_ENDPOINT:-}"
if [ -z "${HF_ENDPOINT}" ]; then
  unset HF_ENDPOINT
fi

echo "[startup] Model name: ${MODEL_NAME}"
echo "[startup] Model repo: ${HF_REPO_ID}"
echo "[startup] Model dir: ${MODEL_DIR}"
echo "[startup] HF_ENDPOINT: ${HF_ENDPOINT:-<not set, using default>}"

# ── Download model if missing ──────────────────────────────────────────────────
if [ ! -d "${MODEL_DIR}" ] || [ -z "$(ls -A ${MODEL_DIR} 2>/dev/null)" ]; then
    echo "[startup] Model not found at ${MODEL_DIR}, downloading..."

    if [ -n "${HF_ENDPOINT}" ]; then
        export HF_ENDPOINT
        echo "[startup] Using HuggingFace mirror: ${HF_ENDPOINT}"
    else
        echo "[startup] Downloading directly from HuggingFace..."
    fi

    python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='${HF_REPO_ID}',
    local_dir='${MODEL_DIR}',
    max_workers=4
)
"

    echo "[startup] Model download complete."
else
    echo "[startup] Model already present at ${MODEL_DIR}, skipping download."
fi

# ── Start the FastAPI service ─────────────────────────────────────────────────
echo "[startup] Starting uvicorn on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info