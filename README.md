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
    │   └── startup.sh
    ├── requirements.txt
    ├── Dockerfile
    └── README.md
```

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
docker build --build-arg MODEL_NAME=Qwen3-0.6B -t inference-service:latest .
docker run -p 8000:8000 inference-service:latest
```

### Test

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"question": "What is Python?", "max_new_tokens": 50}'
```
