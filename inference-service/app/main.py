"""FastAPI inference service for Qwen3-0.6B model."""

import time
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from app.model import load_model, predict
from app.metrics import get_metrics_response, record_request, REQUEST_COUNT

app = FastAPI(title="Serverless AI Platform - Inference Service")


# ── Middleware: track request metrics ─────────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    record_request(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
        duration=duration,
    )
    return response


# ── Request / Response models ─────────────────────────────────────────────────
class PredictRequest(BaseModel):
    question: str
    max_new_tokens: int = 256


class PredictResponse(BaseModel):
    answer: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Liveness probe — returns 200 when the service is up and model is loaded."""
    model, tokenizer = load_model()
    return {"status": "ok", "model_loaded": True, "device": str(model.device)}


@app.post("/predict", response_model=PredictResponse)
async def predict_endpoint(req: PredictRequest):
    """Inference endpoint — runs the model on the given question."""
    answer = predict(req.question, max_new_tokens=req.max_new_tokens)
    return PredictResponse(answer=answer)


@app.get("/metrics")
async def metrics_endpoint() -> PlainTextResponse:
    """Prometheus metrics endpoint — returns text-format metrics."""
    return PlainTextResponse(content=get_metrics_response(), media_type="text/plain")


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    """Load model during server startup to avoid first-request latency."""
    load_model()