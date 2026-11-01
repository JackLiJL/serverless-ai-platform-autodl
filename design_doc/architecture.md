# Serverless AI Platform on AutoDL — Architecture Design Document

## 1. Overview

The inference service can run locally (Docker or bare Python) or on an AutoDL GPU instance. AutoDL currently does not support custom image uploads, so the model is deployed manually on AutoDL by SSH'ing into the instance and running `inference-service/scripts/deploy_autodl.sh` (git clone → install deps → download model → start uvicorn). The monitoring (Prometheus) container is designed to run locally; an SSH tunnel bridges local Prometheus to the remote inference service. Both Docker images (inference + monitoring) are pushed to a registry via CI/CD for future remote deployment. Metrics are pushed to Grafana Cloud for persistent observability.

---

## Module 1: Core Inference Service (FastAPI + HuggingFace)

**Responsibilities:** Serve inference over HTTP and expose Prometheus-compatible metrics. Provide `/health` for liveness, `/predict` for inference, and `/metrics` for monitoring. Load or warm model during startup to avoid first-request latency.

### 1.1 Project Structure

```
inference-service/
├── app/
│   ├── main.py          # FastAPI entrypoint with /health, /predict, /metrics
│   ├── model.py         # HuggingFace model lazy-loading logic
│   └── metrics.py       # Prometheus metrics definitions (Counter, Histogram)
├── requirements.txt     # Python dependencies
├── scripts/
│   ├── startup.sh       # Container entrypoint: downloads model + starts uvicorn
│   └── deploy_autodl.sh # One-shot deployment script for AutoDL host mode
└── Dockerfile           # Base image for AutoDL custom image
```

### 1.2 Key Implementation

**app/metrics.py:**
- `http_requests_total` (Counter) — labeled by method, endpoint, status
- `http_request_duration_seconds` (Histogram) — labeled by method, endpoint
- `get_metrics_response()` — returns Prometheus text format
- `record_request()` — updates both counter and histogram

**app/main.py:**
- Middleware records request metrics (method, endpoint, status, duration)
- `/health` — liveness probe, returns model device info
- `/predict` — POST endpoint accepting JSON `{question, max_new_tokens}`
- `/metrics` — GET endpoint returning Prometheus text format
- Startup event calls `load_model()` to warm the model

**app/model.py:**
- `_get_model_dir()` — resolves model path from `MODEL_DIR` env var or default locations
- `load_model()` — lazy-loads Qwen3-0.6B with `trust_remote_code=True`
- `predict()` — tokenizes input, runs generation with `do_sample=False`, decodes output

---

## Module 2: Docker Build & AutoDL Deployment

**Responsibilities:** Build and push Docker images (inference service + monitoring) to a container registry via CI/CD. On AutoDL (where custom image uploads are not supported), deploy the inference service manually via SSH using the `deploy_autodl.sh` script. The monitoring container is intended to run locally.

### 2.0 Manual AutoDL Deployment (current approach)

Since AutoDL does not support uploading custom images, the deployment on AutoDL is done manually:

1. **SSH into the AutoDL instance**
   ```bash
   ssh -p <ssh_port> root@<instance_ip>
   ```

2. **Run the one-shot deploy script**
   ```bash
   chmod +x /serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh
   /serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh
   ```
   This script:
   - Installs system packages (python3, pip, git, wget, curl)
   - Creates a virtual environment at `.venv`
   - Installs Python dependencies from the Tsinghua PyPI mirror (`pypi.tuna.tsinghua.edu.cn`)
   - Downloads the model (Qwen3-0.6B) from `hf-mirror.com` if not already present
   - Starts uvicorn on port 8000

3. **Create an SSH tunnel from your workstation** (to access the remote API locally)
   ```bash
   ssh -CNg -L 8000:127.0.0.1:8000 root@<instance_ip> -p <ssh_port>
   ```

See `inference-service/run_on_autodl/guide.md` for the full step-by-step guide.

### 2.1 Dockerfile Key Layers (for registry / future remote use)

The Docker image is built and pushed via CI/CD for potential future remote deployment:

```dockerfile
FROM pytorch/pytorch:2.13.0-cuda12.6-cudnn9-runtime

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 sshpass \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (cache layers)
COPY requirements.txt .
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt

# Copy application code only (no model weights)
COPY app/ app/
COPY scripts/ scripts/

# Create models directory (model downloaded at runtime)
RUN mkdir -p /app/models

RUN chmod +x scripts/startup.sh

EXPOSE 8000

ENV MODEL_NAME=Qwen3-0.6B
ENV HF_REPO_ID=Qwen/Qwen3-0.6B
ENV MODEL_DIR=/app/models/${MODEL_NAME}

ENTRYPOINT ["scripts/startup.sh"]
```

### 2.2 Build & Push (both images)

```bash
# Set tag with timestamp for immutable reference
TAG=$(date -u +'%Y%m%d-%H%M%S')

# Build and push inference service image
docker build -t docker.io/<username>/inference-service:${TAG} ./inference-service
docker push docker.io/<username>/inference-service:${TAG}

# Build and push monitoring (Prometheus) image
docker build -t docker.io/<username>/prometheus:${TAG} ./monitoring
docker push docker.io/<username>/prometheus:${TAG}

# Optionally push latest tags
docker tag docker.io/<username>/inference-service:${TAG} docker.io/<username>/inference-service:latest
docker push docker.io/<username>/inference-service:latest
docker tag docker.io/<username>/prometheus:${TAG} docker.io/<username>/prometheus:latest
docker push docker.io/<username>/prometheus:latest
```

Both images are pushed automatically by the CI/CD pipeline (see Module 3).

---

## Module 3: CI/CD Pipeline (GitHub Actions)

**Responsibilities:** Automatically build and push Docker images (inference service + monitoring) to the container registry, and provision Grafana Cloud dashboards via Terraform.

### 3.1 Workflow File: `.github/workflows/docker-build-push.yml`

The workflow:
1. On push to main or manual trigger, builds and pushes two Docker images:
   - `inference-service` (FastAPI app)
   - `prometheus` (monitoring stack)
2. Runs Terraform plan and apply to provision Grafana dashboards

### 3.2 Secrets Required

| Secret | Description |
|--------|-------------|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub password/access token |
| `GRAFANA_URL` | Grafana Cloud URL |
| `GRAFANA_TOKEN` | Grafana API key |
| `PROMETHEUS_DATASOURCE_UID` | Prometheus datasource UID |

### 3.3 Verification Checkpoint
Add secrets to GitHub Secrets and trigger the workflow to verify the build → push → Terraform plan/apply cycle executes end-to-end.

---

## Module 4: Observability (Grafana Cloud)

**Responsibilities:** Preserve metrics and historical trends by pushing metrics to a hosted Prometheus-compatible endpoint (Grafana Cloud). The Prometheus monitoring container runs **locally** on your workstation; an SSH tunnel bridges it to the remote inference service. Provide dashboards and alerting on key signals.

### 4.1 Setup

1. Register a Grafana Cloud free account
2. Navigate to Connections → Add new connection → Prometheus
3. Get Push Gateway URL and API credentials (username/API key)

### 4.2 Application Integration

In `app/main.py`, add a periodic background job to push metrics:

```python
from prometheus_client import push_to_gateway, REGISTRY
from apscheduler.schedulers.background import BackgroundScheduler

def push_metrics():
    push_to_gateway(
        "https://your-handle.grafana.net/api/prom/push",
        job="inference-service",
        registry=REGISTRY,
        basic_auth=("your_username", "your_api_key")
    )

scheduler = BackgroundScheduler()
scheduler.add_job(push_metrics, "interval", seconds=15)
scheduler.start()
```

### 4.3 Dashboards

Example queries for the Grafana dashboard:

| Metric | Query |
|--------|-------|
| Inference QPS | `sum(rate(http_requests_total[5m])) by (method)` |
| P99 Latency | `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` |
| HTTP Status Distribution | `sum by (status) (http_requests_total)` |

### 4.4 Terraform-Managed Dashboard

The project includes a Terraform configuration (`terraform/inference-monitoring/main.tf`) that auto-creates:
- A Grafana folder named "Inference Service"
- A dashboard with panels for:
  - Request rate (QPS) — stat panel with area graph
  - P99 Latency — timeseries panel
  - HTTP Status Code Distribution — pie chart

### 4.5 Running Prometheus Locally

The Prometheus container is designed to run **locally** on your workstation. Configure the scrape target in `prometheus.yml.template` to point to the remote inference service via the SSH tunnel (`localhost:8000`). The `remote_write` configuration pushes metrics to Grafana Cloud.

### 4.6 Verification Checkpoint
During a running test, query the Grafana Explore view for `{job="inference-service"}` and confirm time-series data is present.

---

## Project Structure

```
.
├── design_doc/
│   ├── architecture.md
│   └── mlops_next_steps.md
├── inference-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── model.py
│   │   └── metrics.py
│   ├── scripts/
│   │   ├── startup.sh
│   │   └── deploy_autodl.sh
│   ├── requirements.txt
│   ├── Dockerfile
│   └── run_on_autodl/guide.md
├── monitoring/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── prometheus.yml.template
│   └── .env
├── terraform/
│   ├── providers.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── inference-monitoring/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── .github/workflows/
│   └── docker-build-push.yml
├── .gitignore
└── README.md
```

---

## Quick Start

### Local Development
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

### On AutoDL (manual SSH deployment)
```bash
# 1. SSH into the AutoDL instance
ssh -p <ssh_port> root@<instance_ip>

# 2. Run the one-shot deploy script
chmod +x /serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh
/serverless-ai-platform-autodl/inference-service/scripts/deploy_autodl.sh

# 3. From your workstation, create an SSH tunnel to access the API locally
ssh -CNg -L 8000:127.0.0.1:8000 root@<instance_ip> -p <ssh_port>
```
See `inference-service/run_on_autodl/guide.md` for the full guide.

### Test Endpoints
```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?", "max_new_tokens": 50}'
```

---

## Deliverables & Next Steps

- ✅ This architecture document summarizes all four modules
- ✅ `inference-service/` scaffold exists with `app/`, `scripts/`, `requirements.txt`, `Dockerfile`
- ✅ Manual AutoDL deployment script (`deploy_autodl.sh`) and guide (`run_on_autodl/guide.md`)
- ✅ GitHub Actions workflow configured for build and push
- ✅ Terraform configuration for Grafana dashboard provisioning
- ✅ Monitoring stack with Prometheus remote write to Grafana Cloud (runs locally)

### Optional Follow-ups
- Explore AutoDL custom image support when available; switch to image-based deployment
- Add the full GitHub Actions deploy workflow with SSH automation
- Add model weights to the repository (if small enough) or configure HF token for private models
- See [`mlops_next_steps.md`](./mlops_next_steps.md) for the full MLOps improvement roadmap (Tier 1–4)

---

## Conclusion

This architecture supports running AI inference workloads on AutoDL GPU instances and locally. The inference service is deployed on AutoDL manually via SSH and the `deploy_autodl.sh` script (git clone → install deps → download model → start uvicorn), since AutoDL does not yet support custom image uploads. The monitoring container runs locally, with an SSH tunnel bridging Prometheus to the remote service. Docker images for both components are pushed to a registry via CI/CD, ready for future remote deployment. Persistent observability is maintained through Grafana Cloud, ensuring metrics are preserved even after instance teardown.
