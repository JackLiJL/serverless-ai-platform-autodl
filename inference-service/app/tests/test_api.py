"""Unit tests for FastAPI endpoints — mocked model, TestClient."""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


# ── /health ────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_returns_200(self, test_client: TestClient):
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_response_body(self, test_client: TestClient):
        data = test_client.get("/health").json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert data["device"] == "cpu"


# ── /predict ───────────────────────────────────────────────────────────────────

class TestPredictEndpoint:

    def test_valid_request_returns_answer(self, test_client: TestClient):
        response = test_client.post("/predict", json={"question": "What is Python?"})
        assert response.status_code == 200
        assert response.json()["answer"] == "This is a mocked answer."

    def test_default_max_new_tokens(self, test_client: TestClient):
        """max_new_tokens is optional; the schema default of 256 is used."""
        response = test_client.post("/predict", json={"question": "Hello"})
        assert response.status_code == 200
        assert "answer" in response.json()

    def test_explicit_max_new_tokens(self, test_client: TestClient):
        response = test_client.post(
            "/predict", json={"question": "Hi", "max_new_tokens": 32}
        )
        assert response.status_code == 200

    def test_missing_question_returns_422(self, test_client: TestClient):
        response = test_client.post("/predict", json={"max_new_tokens": 50})
        assert response.status_code == 422
        # Pydantic returns a list of validation error objects
        detail = response.json()["detail"]
        assert any("question" in str(e) for e in detail)

    def test_invalid_max_new_tokens_type_returns_422(self, test_client: TestClient):
        response = test_client.post(
            "/predict", json={"question": "Hello", "max_new_tokens": "not_an_int"}
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, test_client: TestClient):
        response = test_client.post("/predict", json={})
        assert response.status_code == 422


# ── /metrics ───────────────────────────────────────────────────────────────────

class TestMetricsEndpoint:

    def test_returns_200(self, test_client: TestClient):
        response = test_client.get("/metrics")
        assert response.status_code == 200

    def test_content_type_is_text_plain(self, test_client: TestClient):
        response = test_client.get("/metrics")
        assert response.headers["content-type"].startswith("text/plain")

    def test_contains_request_counter_after_health_call(self, test_client: TestClient):
        """After any request, /metrics should include http_requests_total."""
        test_client.get("/health")
        response = test_client.get("/metrics")
        assert "http_requests_total" in response.text

    def test_middleware_records_health_label(self, test_client: TestClient):
        """The metrics middleware records the /health endpoint label."""
        test_client.get("/health")
        response = test_client.get("/metrics")
        assert 'endpoint="/health"' in response.text
