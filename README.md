# Serverless AI Platform on AutoDL

A serverless AI inference platform designed to run on AutoDL cloud GPUs.

## Modules

| Module | Description |
|--------|-------------|
| Module 1 | Core Inference Service — FastAPI + HuggingFace model loader |
| Module 2 | Custom Image Build (AutoDL Image Builder) |
| Module 3 | Lifecycle Manager (AutoDL v2 API) |
| Module 4 | CI/CD Pipeline (GitHub Actions) |
| Module 5 | Observability (Grafana Cloud) |

## Project Structure

```
.
├── design_docs/
│   └── architecture.md
└── inference-service/
    ├── app/
    │   ├── main.py       # FastAPI endpoints
    │   ├── model.py      # Model loader
    │   └── metrics.py    # Prometheus metrics
    ├── scripts/
    │   └── deploy_autodl.sh
    |   └── startup.sh
    ├── requirements.txt
    ├── Dockerfile
    └── README.md
```

## Monitoring

A local Prometheus container with remote write to Grafana Cloud is provided in `monitoring/`.

### Prerequisites
1. SSH tunnel to AutoDL instance:
   ```bash
   ssh -CNg -L 8000:127.0.0.1:8000 root@<autodl_ip> -p <ssh_port>
   ```

2. Grafana Cloud credentials (get from Grafana Cloud → Connections → Prometheus):
   - `GF_PROMETHEUS_URL` — your push endpoint
   - `GF_USER` — your username/email
   - `GF_API_KEY` — an API key with write permissions

### Start Prometheus locally
```bash
cd monitoring

# Build (includes gettext-base for envsubst; env vars are substituted at startup)
# Example: build with a local tag `my-prometheus`
docker build -t my-prometheus .

# Run with env vars. NOTE: if your working directory contains spaces, quote the path.
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
- Check remote write: http://localhost:9091/config (scroll to `remote_write`)
- View metrics in Grafana Cloud Explore

---

## Quick Start

### uvicorn (local)

```bash
cd inference-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
MODEL_DIR=/path/to/model uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build image (no model — just runtime + code, ~2GB)
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

### CI/CD notes

- The repository's GitHub Actions workflow (`.github/workflows/docker-build-push.yml`) now generates a timestamp-style Docker tag of the form `YYYYMMDD-HHMMSS` and uses that as the primary image tag pushed to the registry. If you build/push from the default branch the workflow can also push the `latest` tag.
- When referring to CI-pushed images in deployment manifests, prefer the timestamp tag (stable immutable reference) or `latest` for convenience.

### Test

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"question": "What is Python?", "max_new_tokens": 50}'
```
