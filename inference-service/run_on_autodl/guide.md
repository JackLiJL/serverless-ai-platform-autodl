# Server Setup & Inference Guide

**Recommended hardware:** RTX 4090D (24 GB) — helpful for GPU inference. The instructions below work on any Linux server; adjust paths and privileges as needed.

The reason why this guide exists at all: AutoDL failed to pull docker image from docker hub, and the instance itself is a container. So we will have to git clone the code and run it within the container.

Given the trial and error, a written automation deploy shell script in AutoDL container can be found at `inference-service/scripts/deploy_autodl.sh`, which can be run with
```
chmod +x /serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh
/serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh
```

---

## 1) Connect and prepare the environment

SSH into the server, install runtime tools, clone the repository, and create a Python virtual environment:

```bash
# connect to the server
ssh -p <ssh_port> root@<instance_ip>

# update package lists and install required system packages
apt update && apt install -y python3 python3-venv python3-pip git wget

# clone the repository into `/serverless-ai-platform-autodl` (skip if already mounted)
git clone https://github.com/JackLiJL/serverless-ai-platform-autodl.git /serverless-ai-platform-autodl || true
cd /serverless-ai-platform-autodl/inference-service

# create and activate a virtual environment (absolute path)
python3 -m venv /serverless-ai-platform-autodl/inference-service/.venv
source /serverless-ai-platform-autodl/inference-service/.venv/bin/activate

# upgrade pip and install Python dependencies (use the mirror if you prefer)
python -m pip install --upgrade pip
pip install --no-cache-dir -r /serverless-ai-platform-autodl/inference-service/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 2) Download model parameters

The startup script will download model files automatically if `models/<MODEL_NAME>` is missing. To pre-download weights manually:

```bash
# create model folder (absolute path) and download files
mkdir -p /serverless-ai-platform-autodl/inference-service/models/Qwen3-0.6B
cd /serverless-ai-platform-autodl/inference-service/models/Qwen3-0.6B

# replace these URLs with your mirror or the official Hugging Face links
wget -c https://hf-mirror.com/Qwen/Qwen3-0.6B/resolve/main/model.safetensors
wget -c https://hf-mirror.com/Qwen/Qwen3-0.6B/resolve/main/config.json
wget -c https://hf-mirror.com/Qwen/Qwen3-0.6B/resolve/main/tokenizer.json
wget -c https://hf-mirror.com/Qwen/Qwen3-0.6B/resolve/main/tokenizer_config.json

cd /serverless-ai-platform-autodl/inference-service
```

**Notes:**
- If downloading on the server, prefer a nearby mirror to reduce transfer time and avoid rate limits.
- The repository's `scripts/startup.sh` downloads the model when the target model directory is empty.

---

## 3) Start the service and create an SSH tunnel

Make the startup script executable and start the service. Use an SSH tunnel from your workstation to access the API securely.

```bash
# on the server (use absolute path)
chmod +x /serverless-ai-platform-autodl/inference-service/scripts/startup.sh
/serverless-ai-platform-autodl/inference-service/scripts/startup.sh

# on your local machine, forward remote port 8000 to localhost
ssh -CNg -L 8000:127.0.0.1:8000 root@<instance_ip> -p <ssh_port>
```
