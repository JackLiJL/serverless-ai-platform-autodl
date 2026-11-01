# MLOps Next Steps — Improvement Roadmap

This document outlines prioritized improvements to the current inference service, organized by MLOps maturity tier. Each tier builds on the previous.

## Current State

| Component | Status |
|---|---|
| FastAPI service (`/health`, `/predict`, `/metrics`) | Working, minimal |
| Model loading (Qwen3-0.6B from local dir) | Working, manual |
| Prometheus metrics (request count, latency) | Basic |
| Prometheus Docker container (local) | Working |
| Grafana Cloud remote_write | Configured |
| Terraform dashboard provisioning | Working |
| Docker build/push (both images) | Working via CI |
| AutoDL manual deploy | Working via SSH |

**Known gaps:**
- No tests
- No structured logging (raw `print()` statements)
- No configuration management (scattered env vars)
- No request concurrency control
- No model versioning
- Unpinned dependencies
- No CI test step
- No GPU/resource metrics
- No graceful shutdown
- No prompt/response logging for offline evaluation
- No API auth

---

## Tier 1: Foundation — Testable & Reproducible

> *"You can't manage what you can't measure."*

### 1.1 Reproducible Dependencies

- **What:** Replace unpinned `requirements.txt` with `uv` (or `poetry`) + lock file
- **Files:** `inference-service/pyproject.toml`, `inference-service/uv.lock`
- **Learn:** dependency management, deterministic builds

### 1.2 Test Suite

- **What:** Add `pytest` tests
  - `tests/test_model.py` — mock HF model, test `predict()` output, test `load_model()` caching
  - `tests/test_api.py` — `TestClient` integration tests for all 3 endpoints
  - `tests/test_metrics.py` — verify Prometheus counters/histograms increment correctly
- **Files:** `inference-service/tests/`, `inference-service/conftest.py`
- **Learn:** test-driven development for ML services

### 1.3 CI Test Gate

- **What:** Add a `test` job to the GitHub Actions workflow that runs `pytest` *before* the Docker build step
- **Files:** `.github/workflows/docker-build-push.yml`
- **Learn:** shift-left quality gates, multi-job pipelines

### 1.4 Structured Logging

- **What:** Replace all `print()` with `structlog` (JSON to stdout). Add log levels, request IDs
- **Files:** `inference-service/app/logging_config.py`, update `model.py` and `main.py`
- **Learn:** observability foundations, container-friendly logging

---

## Tier 2: Service Hardening — Production-Ready API

> *"Treat your model service like any other microservice."*

### 2.1 Configuration Management

- **What:** Create `app/config.py` using `pydantic-settings`. Consolidate all env vars into a typed `Settings` class with validation and defaults
- **Files:** `inference-service/app/config.py`
- **Learn:** 12-factor app config, env var validation

### 2.2 Concurrency Control

- **What:** Add `asyncio.Semaphore(1)` to serialize GPU inferences. Return `429 Too Many Requests` when the queue is full
- **Files:** `inference-service/app/main.py`
- **Learn:** backpressure, resource management under contention

### 2.3 Graceful Shutdown

- **What:** Add `SIGTERM` handler — stop accepting new requests, let in-flight predictions finish, then exit cleanly
- **Files:** `inference-service/app/main.py`, `inference-service/Dockerfile` (update `ENTRYPOINT`)
- **Learn:** container lifecycle, zero-downtime deployments

### 2.4 API Authentication

- **What:** Add `X-API-Key` header middleware for `/predict`. Configurable via `API_KEY` env var (optional in dev)
- **Files:** `inference-service/app/main.py`, `inference-service/app/config.py`
- **Learn:** service-to-service auth, middleware patterns

### 2.5 Input Validation & Safety

- **What:** Add max input length check, cap `max_new_tokens`, structured error responses (400/422/500 with JSON body)
- **Files:** `inference-service/app/main.py`, `inference-service/app/model.py`
- **Learn:** defensive programming, error contract design


---

## Tier 3: ML-Specific MLOps

> *"Models are assets that need lifecycle management."*

### 3.1 Model Versioning

- **What:** Track loaded model version (name + file hash + timestamp). Expose in `/health`. Support `MODEL_VERSION` env var
- **Files:** `inference-service/app/model.py`, `inference-service/app/main.py`
- **Learn:** model lineage, auditability

### 3.2 Prompt/Response Logging

- **What:** Log every `/predict` request + response to JSONL file (timestamp, model version, input, output, latency, token counts). This becomes the offline evaluation dataset
- **Files:** `inference-service/app/eval_log.py`, wired into `main.py`
- **Learn:** data flywheel, offline model evaluation

### 3.3 GPU Resource Metrics

- **What:** Add Prometheus gauges for `gpu_memory_used_bytes`, `gpu_utilization` (read from `nvidia-smi` via subprocess, or PyTorch `torch.cuda`). Add Grafana panels
- **Files:** `inference-service/app/metrics.py`, `terraform/inference-monitoring/main.tf`
- **Learn:** ML-specific observability, GPU monitoring

### 3.4 Model Hot-Swap

- **What:** Add `/reload-model` admin endpoint that swaps to a new model from disk without restarting the service
- **Files:** `inference-service/app/model.py`, `inference-service/app/main.py`
- **Learn:** zero-downtime model updates, model CI/CD

---

## Tier 4: Advanced — CI/CD & Monitoring Maturity

### 4.1 Enhanced CI Pipeline

- **What:** Expand the workflow to include: `ruff` lint + `mypy` type check, `pytest`, Docker build with layer cache, conditional push
- **Files:** `.github/workflows/docker-build-push.yml`
- **Learn:** multi-stage CI, static analysis in pipelines

### 4.2 Alerting Rules

- **What:** Add Prometheus alert rules for: P99 latency > 10s, error rate > 5%, GPU memory > 90%. Wire into Grafana alerting
- **Files:** `monitoring/alert_rules.yml`, `terraform/inference-monitoring/main.tf`
- **Learn:** SLOs, alert fatigue management

### 4.3 Local Docker Compose Stack

- **What:** Add `docker-compose.yml` for the full local stack: inference service + Prometheus + optional local Grafana OSS. One command: `docker compose up`
- **Files:** `docker-compose.yml` (repo root)
- **Learn:** local dev environments that mirror production

### 4.4 Model Download Pipeline

- **What:** Script that: downloads new model version → validates with a test prompt → updates `MODEL_DIR` → triggers hot-swap. Automate via cron or GitHub Actions schedule
- **Files:** `inference-service/scripts/download_model.py`
- **Learn:** model CI/CD, automated model updates

---

## Suggested Execution Order

| Step | Item | Est. Effort |
|---|---|---|
| 1 | 1.4 Structured Logging | Small |
| 2 | 1.2 Test Suite | Medium |
| 3 | 1.3 CI Test Gate | Small |
| 4 | 1.1 Reproducible Dependencies | Medium |
| 5 | 2.1 Configuration Management | Medium |
| 6 | 2.2 Concurrency Control | Small |
| 7 | 2.5 Input Validation & Safety | Small |
| 8 | 3.1 Model Versioning | Medium |
| 9 | 3.3 GPU Resource Metrics | Medium |
| 10 | 3.2 Prompt/Response Logging | Medium |
| 11 | 4.3 Docker Compose Stack | Small |
| 12 | 4.1 Enhanced CI Pipeline | Medium |

> Start with **Tier 1** (steps 1–4): lowest risk, highest learning ROI, and makes all subsequent tiers easier to build.

---

## Related Documents

- [`architecture.md`](./architecture.md) — full system design and module breakdown
- `inference-service/run_on_autodl/guide.md` — manual AutoDL deployment guide

