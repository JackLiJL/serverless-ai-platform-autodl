"""Prometheus metrics for inference service."""

from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time

# Request counter: total HTTP requests labeled by method, endpoint, status
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY,
)

# Latency histogram: request duration in seconds labeled by method, endpoint
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

def get_metrics_response():
    """Return Prometheus text-format metrics string."""
    return generate_latest().decode('utf-8')

def record_request(method: str, endpoint: str, status: int, duration: float):
    """Record a single request to both counter and histogram."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)