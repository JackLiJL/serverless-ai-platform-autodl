FROM pytorch/pytorch:2.13.0-cuda12.6-cudnn9-runtime

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (cache layers)
COPY requirements.txt .
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt

# Copy application code only (no model weights)
COPY app/ app/
COPY scripts/ scripts/

# Create models directory (model downloaded at runtime)
RUN mkdir -p /app/models

# Make startup script executable
RUN chmod +x scripts/startup.sh

EXPOSE 8000

# MODEL_DIR and MODEL_NAME are set at runtime via environment variables
# Default model name if not provided
ENV MODEL_NAME=Qwen3-0.6B
ENV HF_REPO_ID=Qwen/Qwen3-0.6B
ENV MODEL_DIR=/app/models/${MODEL_NAME}
# Do not set HF_ENDPOINT to an empty string here; keep it undefined unless a mirror is used.

ENTRYPOINT ["scripts/startup.sh"]
