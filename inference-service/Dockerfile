FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

ARG MODEL_NAME=Qwen3-0.6B
ARG MODEL_SOURCE=/models/${MODEL_NAME}

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (cache layers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY scripts/ scripts/

# Create models directory and copy default model (if available at build time)
RUN mkdir -p /app/models && \
    if [ -d "/models" ]; then cp -r /models/* /app/models/; fi

# Make startup script executable
RUN chmod +x scripts/startup.sh

EXPOSE 8000

# MODEL_DIR can be overridden at runtime via docker run -e MODEL_DIR=/path/to/model
ENV MODEL_DIR=/app/models/${MODEL_NAME}

ENTRYPOINT ["scripts/startup.sh"]
