#!/bin/bash
# deploy_autodl.sh - One-shot deployment script for the AutoDL inference service (host mode)
# Assumes: the repo has been cloned to /root/serverless-ai-platform-autodl
# Usage: from anywhere, just run this script (e.g., /root/deploy_autodl.sh)

set -e  # exit immediately on error

# ========== Absolute paths ==========
REPO_ROOT="/root/serverless-ai-platform-autodl"
SERVICE_DIR="$REPO_ROOT/inference-service"
MODEL_BASE_DIR="$SERVICE_DIR/models"

# ========== Color output ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ========== Configuration (editable) ==========
MODEL_NAME="Qwen3-0.6B"
MODEL_REPO="Qwen/Qwen3-0.6B"
HF_MIRROR="https://hf-mirror.com"
PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"
SERVICE_PORT="8000"

# ========== Verify the service directory exists ==========
if [ ! -d "$SERVICE_DIR" ]; then
    log_error "Service directory $SERVICE_DIR not found."
    log_error "Please clone the repo: git clone https://github.com/JackLiJL/serverless-ai-platform-autodl.git $REPO_ROOT"
    exit 1
fi

cd "$SERVICE_DIR"

# ========== Verify we are in the project root ==========
if [ ! -f "requirements.txt" ] || [ ! -d "app" ]; then
    log_error "The service directory does not contain app/ and requirements.txt. Please check the repo structure."
    exit 1
fi

# ========== 1. Install system packages ==========
log_info "Installing system packages..."
apt update -qq && apt install -y -qq python3 python3-pip git wget curl

# ========== 2. Create virtual environment (if missing) ==========
if [ -d ".venv" ]; then
    log_info "Virtual environment already exists, using it."
else
    log_info "Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# ========== 3. Install Python dependencies ==========
log_info "Installing Python dependencies (using $PYPI_MIRROR)..."
pip install -r requirements.txt -i $PYPI_MIRROR -q

# ========== 4. Download model (if missing) ==========
MODEL_DIR="$MODEL_BASE_DIR/$MODEL_NAME"
if [ ! -f "$MODEL_DIR/model.safetensors" ]; then
    log_info "Downloading model $MODEL_NAME into $MODEL_DIR ..."
    mkdir -p "$MODEL_DIR"
    cd "$MODEL_DIR"

    # use wget -c (supports resume) to download required files
    for file in model.safetensors config.json tokenizer.json tokenizer_config.json special_tokens_map.json generation_config.json; do
        log_info "  Downloading $file ..."
        wget -c -q "$HF_MIRROR/$MODEL_REPO/resolve/main/$file" || {
            log_warn "  $file failed to download; retrying..."
            wget -c -q "$HF_MIRROR/$MODEL_REPO/resolve/main/$file"
        }
    done

    cd "$SERVICE_DIR"
else
    log_info "Model already exists; skipping download"
fi

# ========== 5. Verify model files ==========
if [ ! -f "$MODEL_DIR/model.safetensors" ]; then
    log_error "Model file model.safetensors not found; download failed"
    exit 1
fi
log_info "Model file verification passed"

# ========== 6. Start the service ==========
log_info "Starting the inference service (port $SERVICE_PORT) ..."
log_info "Press Ctrl+C to stop"
export MODEL_DIR="$MODEL_DIR"
uvicorn app.main:app --host 0.0.0.0 --port $SERVICE_PORT
