"""Integration tests — run against a live running container.

Requires:
  - A running inference service (with model loaded) at SERVICE_URL
  - Default SERVICE_URL: http://localhost:8000

Run locally:
  export SERVICE_URL=http://localhost:8000
  pytest integration/ -m integration -v

Run in CI:
  docker run -d --name inference-test -p 8000:8000 inference-service:test
  pytest integration/ -m integration -v
"""
import pytest
import requests

pytestmark = pytest.mark.integration


# ── /health ────────────────────────────────────────────────────────────────────

class TestHealth:

    def test_returns_200(self, service_url):
        response = requests.get(f"{service_url}/health", timeout=10)
        assert response.status_code == 200

    def test_model_loaded(self, service_url):
        data = requests.get(f"{service_url}/health", timeout=10).json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True

    def test_device_field_present(self, service_url):
        data = requests.get(f"{service_url}/health", timeout=10).json()
        assert "device" in data
        assert data["device"] in ("cpu", "cuda")


# ── /predict ───────────────────────────────────────────────────────────────────

class TestPredict:

    def test_returns_non_empty_answer(self, service_url):
        """A real model call returns a non-empty string answer."""
        response = requests.post(
            f"{service_url}/predict",
            json={"question": "What is Python?", "max_new_tokens": 64},
            timeout=180,  # CPU inference on a 0.6B model can take ~30 s
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"].strip()) > 0

    def test_missing_question_returns_422(self, service_url):
        """Omitting the required 'question' field returns 422."""
        response = requests.post(
            f"{service_url}/predict",
            json={"max_new_tokens": 32},
            timeout=30,
        )
        assert response.status_code == 422

    def test_invalid_max_new_tokens_returns_422(self, service_url):
        """A non-integer max_new_tokens returns 422."""
        response = requests.post(
            f"{service_url}/predict",
            json={"question": "Hello", "max_new_tokens": "abc"},
            timeout=30,
        )
        assert response.status_code == 422


# ── /metrics ───────────────────────────────────────────────────────────────────

class TestMetrics:

    def test_returns_200(self, service_url):
        response = requests.get(f"{service_url}/metrics", timeout=10)
        assert response.status_code == 200

    def test_content_type_is_text_plain(self, service_url):
        response = requests.get(f"{service_url}/metrics", timeout=10)
        assert "text/plain" in response.headers.get("content-type", "")

    def test_contains_request_counter(self, service_url):
        """After calling /health, /metrics includes http_requests_total."""
        requests.get(f"{service_url}/health", timeout=10)
        response = requests.get(f"{service_url}/metrics", timeout=10)
        assert "http_requests_total" in response.text

    def test_contains_latency_histogram(self, service_url):
        """After any request, /metrics includes http_request_duration_seconds."""
        requests.get(f"{service_url}/health", timeout=10)
        response = requests.get(f"{service_url}/metrics", timeout=10)
        assert "http_request_duration_seconds" in response.text

    def test_middleware_records_health_label(self, service_url):
        """The middleware records the /health endpoint label in metrics."""
        requests.get(f"{service_url}/health", timeout=10)
        response = requests.get(f"{service_url}/metrics", timeout=10)
        assert 'endpoint="/health"' in response.text
