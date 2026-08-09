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

Responsibilities: Produce a container image that AutoDL can start directly (AutoDL instances run containers themselves and do not support nested Docker). The image must contain the runtime, Python dependencies, and optionally pre-downloaded model weights.

Build guidance:
- Base the image on an appropriate PyTorch/CUDA runtime if GPU support is needed.
- Install dependencies from `requirements.txt` using a reliable mirror.
- Optionally pre-download model weights during image build to reduce cold-start time at the expense of larger image size. If you avoid baking weights into the image, use a startup script to download them on first run.
- Copy the `app/` and `scripts/` into the image, ensure the startup script is executable, expose the serving port, and set the entrypoint to the startup script.

Publishing: Push the built image to a registry AutoDL prefers (the document suggests the Alibaba Cloud registry for best pull performance on AutoDL) or Docker Hub.

Verification checkpoint: Confirm the pushed image is discoverable in the AutoDL console under custom images.

---

## Module 3 — Lifecycle Manager

Responsibilities: Create, monitor, and destroy AutoDL instances through the AutoDL v2 API to ensure resources are provisioned for tests or ephemeral workloads and fully released afterward.

Implementation highlights:
- Implement a small client that calls AutoDL API endpoints to create an instance with a given image, poll instance status until `running`, retrieve SSH credentials or instance IP, and destroy the instance when work finishes.
- Provide a `wait_for_running` loop with a timeout and backoff to handle provisioning delays.

Deployment/SSH automation:
- If your custom image already contains the application and startup logic, you only need to issue a restart via SSH or API. If not, automate code upload with `scp`/`rsync` (or `sshpass` in CI) and start the service remotely.

Verification checkpoint: From your development machine, run the lifecycle script to create and then destroy a test instance (use the cheapest CPU instance for API validation to avoid costs).

---

## Module 4 — CI/CD Pipeline (GitHub Actions)

Responsibilities: Wire the image build, instance creation, functional verification, and teardown into an automated pipeline that can be triggered on push or manually.

Workflow guidance:
- Checkout the repository, build and push the image to the selected registry.
- Use the lifecycle manager to create an instance with the new image.
- Wait for the instance to become healthy, then run quick inference calls against `/predict` to validate functionality.
- Destroy the instance as the final step to ensure no resources remain allocated.

Secrets and configuration: Store `AUTODL_TOKEN` and any registry credentials in GitHub Secrets. Parameterize the image identifier used for deployment.

Verification checkpoint: Add `AUTODL_TOKEN` to GitHub Secrets and trigger the workflow to verify the create → test → destroy cycle executes end-to-end.

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

