"""Unit tests for app.metrics — verify Prometheus counter and histogram behaviour."""
import pytest
from prometheus_client import REGISTRY

from app import metrics as metrics_mod

pytestmark = pytest.mark.unit



def _counter_value(method: str, endpoint: str, status: int) -> float:
    """Read the current value for a specific label combination."""
    val = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": method, "endpoint": endpoint, "status": str(status)},
    )
    return val if val is not None else 0.0


# ── record_request() ───────────────────────────────────────────────────────────

def test_record_request_increments_counter():
    """Calling record_request() increases http_requests_total by 1."""
    before = _counter_value("GET", "/test_unique_1", 200)
    metrics_mod.record_request(method="GET", endpoint="/test_unique_1", status=200, duration=0.05)
    after = _counter_value("GET", "/test_unique_1", 200)
    assert after == before + 1


def test_record_request_records_histogram():
    """Calling record_request() registers a sample in the latency histogram."""
    # Use a unique endpoint so we don't collide with other tests
    endpoint = "/test_unique_hist"
    metrics_mod.record_request(
        method="POST", endpoint=endpoint, status=500, duration=0.75
    )
    response = metrics_mod.get_metrics_response()
    assert "http_request_duration_seconds" in response
    assert f'endpoint="{endpoint}"' in response


# ── get_metrics_response() ─────────────────────────────────────────────────────

def test_metrics_response_is_prometheus_text_format():
    """get_metrics_response() returns a valid Prometheus text format string."""
    response = metrics_mod.get_metrics_response()
    # Prometheus text format always starts with # HELP or # TYPE comments
    assert response.strip().startswith("#")


def test_metrics_response_contains_counter_metric_name():
    """The response includes the http_requests_total metric name."""
    # Record a request first so the metric has at least one data point
    metrics_mod.record_request(method="GET", endpoint="/test_unique_2", status=200, duration=0.01)
    response = metrics_mod.get_metrics_response()
    assert "http_requests_total" in response


def test_metrics_response_contains_histogram_metric_name():
    """The response includes the http_request_duration_seconds metric name."""
    metrics_mod.record_request(method="GET", endpoint="/test_unique_3", status=200, duration=0.01)
    response = metrics_mod.get_metrics_response()
    assert "http_request_duration_seconds" in response


# ── accumulation ───────────────────────────────────────────────────────────────

def test_counter_accumulates_across_calls():
    """Multiple calls to record_request() accumulate the counter."""
    endpoint = "/test_accumulate"
    metrics_mod.record_request("GET", endpoint, 200, 0.01)
    metrics_mod.record_request("GET", endpoint, 200, 0.02)
    metrics_mod.record_request("GET", endpoint, 200, 0.03)
    # Should have exactly 3 recorded (or 3 + any prior test pollution on same label)
    # We use a unique endpoint name to guarantee exactly 3
    assert _counter_value("GET", endpoint, 200) == 3
