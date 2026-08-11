# Serverless AI Platform on AutoDL — Architecture Design Document

This document summarizes the engineering architecture for running an inference service on the AutoDL platform. It covers five modules: Core Inference Service, Custom Image Building, Lifecycle Management, CI/CD pipeline, and Observability. Each module includes responsibilities, implementation highlights, and verification checkpoints.

## Module 1 — Core Inference Service (FastAPI + HuggingFace)

Responsibilities: Serve inference over HTTP and expose Prometheus-compatible metrics. Provide `/health` for liveness, `/predict` for inference, and `/metrics` for monitoring. Load or warm model during startup to avoid first-request latency.

Project layout (recommended): a top-level `inference-service/` folder containing an `app/` package (FastAPI entry, model loader, metrics definitions), a `scripts/` folder (startup script), a `requirements.txt`, and a `Dockerfile` for building the runtime image.

Implementation highlights:
- Define Prometheus metrics such as request counters and latency histograms and register them with a registry.
- Load the HuggingFace model lazily on startup or during a warm-up step to mitigate slow first requests.
- Expose `/metrics` in Prometheus text format so AutoDL or a local scrape can collect metrics, and optionally schedule periodic pushes to a remote Prometheus Push endpoint (Grafana Cloud) if scrape is not available.

Verification checkpoint: Run the service locally (e.g. with Uvicorn) and confirm the `/metrics` endpoint returns Prometheus-format metrics.

---

## Module 2 — Custom Image Build (AutoDL Image Builder)

Responsibilities: Produce a lightweight container image that AutoDL can start directly. The image contains only the runtime environment (PyTorch/CUDA, Python, and pip dependencies) — no application code and no model weights. This keeps the image small (~2 GB), fitting within free-tier registry quotas.

Build guidance:
- Base the image on an appropriate PyTorch/CUDA runtime if GPU support is needed.
- Install dependencies from `requirements.txt` using a reliable mirror.
- Do not copy application code or model weights into the image.
- Set the container entrypoint to `sleep infinity` so the container stays alive and accepts SSH connections after AutoDL starts it.

Publishing: Push the built image to a registry AutoDL prefers (e.g. Alibaba Cloud Container Registry) or Docker Hub.

Verification checkpoint: Confirm the pushed image is discoverable in the AutoDL console under custom images.

---

## Module 3 — Lifecycle Manager

Responsibilities: Create, monitor, and destroy AutoDL instances through the AutoDL v2 API to ensure resources are provisioned for tests or ephemeral workloads and fully released afterward.

Implementation highlights:
- Implement a small client that calls AutoDL API endpoints to create an instance with the lightweight base image, poll instance status until `running`, retrieve SSH credentials or instance IP, and destroy the instance when work finishes.
- Provide a `wait_for_running` loop with a timeout and backoff to handle provisioning delays.

Deployment/SSH automation:
- After the instance is running, SSH into the container.
- Clone the application code repository inside the container.
- Check if model weights already exist; if not, download them from HuggingFace (optionally using `HF_ENDPOINT=https://hf-mirror.com` for domestic mirror acceleration when the AutoDL node is in an overseas region).
- Start the FastAPI service in the background (e.g. via `nohup`).
- The lifecycle manager orchestrates this entire sequence as part of the deployment workflow.

Key considerations:
- Because the instance is fully destroyed after each run, the data disk is wiped. The model must be re-downloaded on every startup — the existence check (`if [ ! -d "$MODEL_DIR" ]`) will always be true.
- Health checks must account for the model download time (5–10 minutes). Use a generous retry window (10–15 minutes) in the CI/CD pipeline before marking the deployment as failed.
- Optional optimization: If download time or bandwidth is a concern, a first manual run can leave the instance in "stop" (not destroy) mode with the data disk preserved, so subsequent starts skip the download. However, this requires not calling the destroy endpoint, which conflicts with the "用完即焚" (teardown after use) approach.

Verification checkpoint: From your development machine, run the lifecycle script to create and then destroy a test instance (use the cheapest CPU instance for API validation to avoid costs).

---

## Module 4 — CI/CD Pipeline (GitHub Actions)

Responsibilities: Wire the image build, instance creation, code/model setup via SSH, functional verification, and teardown into an automated pipeline that can be triggered on push or manually.

Workflow guidance:
- Build and push the lightweight runtime image to the container registry.
- Use the lifecycle manager to create an AutoDL instance with that image.
- SSH into the running container and run the setup sequence: clone the code repo, check if model exists (download if missing), start the service.
- Wait for the model to download (5–10 min) and load into GPU memory. Use a generous retry loop (10–15 minutes, checking `/health` every 30–60 seconds) before failing.
- Run quick inference calls against `/predict` to validate functionality.
- Destroy the instance as the final step to ensure no resources remain allocated.
- Use a manual approval gate between the test step and teardown so the instance can be inspected or manually used before destruction.

Secrets and configuration: Store `AUTODL_TOKEN`, SSH password, HuggingFace token, and any registry credentials in GitHub Secrets. Parameterize the image identifier and model name used for deployment.

Verification checkpoint: Add secrets to GitHub Secrets and trigger the workflow to verify the create → SSH setup → test → destroy cycle executes end-to-end.

---

## Module 5 — Observability (Grafana Cloud)

Responsibilities: Preserve metrics and historical trends even after instances are terminated by pushing metrics to a hosted Prometheus-compatible endpoint (Grafana Cloud). Provide dashboards and alerting on key signals.

Integration guidance:
- Register a Grafana Cloud free account and configure a Prometheus remote push endpoint (or Pushgateway) and API credentials.
- In the inference application, add a periodic background job to push the local registry to the remote endpoint if scraping is not available.
- Keep credentials in environment variables (for example, `GF_USER` and `GF_PASS` or an API key) and do not embed them in code.

Dashboards / example queries:
- Inference QPS: `rate(http_requests_total[1m])`
- P99 latency: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[1m]))`

Verification checkpoint: During a running test, query the Grafana Explore view for metrics with the job label (for example `job="inference-service"`) and confirm time-series data is present.

---

## Deliverables & Next Steps

- This file is the canonical design specification in `design_doc/architecture.md`.
- Create or verify an `inference-service/` layout that follows this specification: `app/`, `scripts/`, `requirements.txt`, and `Dockerfile`.
- Configure GitHub Actions secrets and progressively enable the CI/CD workflow.

Optional follow-ups I can implement for you:
- Generate a minimal runnable `inference-service` scaffold (application layout, `requirements.txt`, and a `startup.sh` script) and add it to the repository.
- Create the lifecycle manager script and a GitHub Actions workflow stub in `.github/workflows/`.