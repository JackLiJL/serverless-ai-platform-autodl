# Serverless AI Platform on AutoDL

An AI inference platform that runs LLM models (Qwen3-0.6B) on AutoDL cloud GPUs or locally. The inference service is deployed to AutoDL manually via SSH (since AutoDL does not yet support custom image uploads). Monitoring runs locally via a Prometheus container that connects to the remote service over an SSH tunnel. Both Docker images are pushed to a registry via CI/CD for future remote deployment.

## Modules

| Module | Description |
|--------|-------------|
| Module 1 | Core Inference Service — FastAPI + HuggingFace model loader |
| Module 2 | Docker Build & AutoDL Deployment (manual SSH) |
| Module 3 | CI/CD Pipeline (GitHub Actions) |
| Module 4 | Observability (Grafana Cloud + local Prometheus) |

Full architecture: see [`design_doc/architecture.md`](./design_doc/architecture.md)

## Project Structure

```
.
├── design_doc/
│   ├── architecture.md          # System design document
│   └── mlops_next_steps.md      # MLOps improvement roadmap
├── inference-service/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints
│   │   ├── model.py             # Model loader
│   │   └── metrics.py           # Prometheus metrics
│   ├── scripts/
│   │   ├── deploy_autodl.sh     # One-shot AutoDL deploy (SSH)
│   │   └── startup.sh           # Container entrypoint
│   ├── run_on_autodl/
│   │   └── guide.md             # Step-by-step AutoDL deployment guide
│   ├── requirements.txt
│   └── Dockerfile
├── monitoring/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── prometheus.yml.template
│   └── .env                     # Grafana Cloud credentials
├── terraform/
│   ├── providers.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── inference-monitoring/    # Grafana Cloud dashboard via Terraform
├── .github/workflows/
│   └── docker-build-push.yml    # CI: build + push both Docker images
├── .gitignore
└── README.md
```

## Quick Start

### On AutoDL (manual SSH deployment)

The current way to run the service on an AutoDL GPU instance:

```bash
# 1. SSH into the AutoDL instance
ssh -p <ssh_port> root@<instance_ip>

# 2. Run the one-shot deploy script
chmod +x /serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh
/serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh

# 3. From your workstation, create an SSH tunnel to access the API locally
ssh -CNg -L 8000:127.0.0.1:8000 root@<instance_ip> -p <ssh_port>
```

See `inference-service/run_on_autodl/guide.md` for the full step-by-step guide.

### Local Development (bare Python)

```bash
cd inference-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
MODEL_DIR=/path/to/model uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build image (no model — runtime + code only, ~2GB)
docker build -t inference-service:latest .

# Run with model downloaded at startup
docker run -p 8000:8000 \
  -e MODEL_NAME=Qwen3-0.6B \
  inference-service:latest
```

Optionally use HuggingFace mirror for faster downloads (China-based AutoDL nodes):

```bash
docker run -p 8000:8000 \
  -e MODEL_NAME=Qwen3-0.6B \
  -e HF_ENDPOINT=https://hf-mirror.com \
  inference-service:latest
```

### Test Endpoints

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?", "max_new_tokens": 50}'
```

## Monitoring (local Prometheus → Grafana Cloud)

A local Prometheus container with remote write to Grafana Cloud is provided in `monitoring/`.

### Prerequisites

1. SSH tunnel to AutoDL instance (if running the service remotely):
   ```bash
   ssh -CNg -L 8000:127.0.0.1:8000 root@<autodl_ip> -p <ssh_port>
   ```

2. Grafana Cloud credentials (from Grafana Cloud → Connections → Prometheus):
   - `GF_PROMETHEUS_URL` — your push endpoint
   - `GF_USER` — your username/email
   - `GF_API_KEY` — an API key with write permissions

   These go in `monitoring/.env` (do not commit to git).

### Start Prometheus locally

```bash
cd monitoring

# Build the image
docker build -t my-prometheus .

# Run with env vars (quote the path if your working directory contains spaces)
docker run -d \
  --name prometheus \
  -p 9091:9090 \
  -v "$(pwd)/.env:/etc/prometheus/.env:ro" \
  --env-file "$(pwd)/.env" \
  my-prometheus
```

### Access

| Service | URL |
|---------|-----|
| Prometheus UI | http://localhost:9091 |
| Grafana Cloud | https://grafana.com |

### Verify

- Check scrape targets: http://localhost:9091/targets (should show `inference-service` as UP)
- Check remote write config: http://localhost:9091/config
- View metrics in Grafana Cloud Explore

## CI/CD

The GitHub Actions workflow (`.github/workflows/docker-build-push.yml`) builds and pushes **two** Docker images on every push to `main`:

| Image | Context | Registry tag |
|---|---|---|
| Inference service | `./inference-service` | `<username>/inference-service:YYYYMMDD-HHMMSS` |
| Prometheus monitoring | `./monitoring` | `<username>/prometheus:YYYYMMDD-HHMMSS` |

Both images are tagged with a timestamp (immutable) and optionally `latest`. The workflow also runs Terraform to provision Grafana Cloud dashboards.

## MLOps Roadmap

See [`design_doc/mlops_next_steps.md`](./design_doc/mlops_next_steps.md) for the prioritized improvement plan across 4 tiers: Foundation → Service Hardening → ML-Specific MLOps → Advanced CI/CD.

