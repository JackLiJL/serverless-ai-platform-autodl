"""Fixtures for integration tests — require a running inference service container."""
import os
import time
import requests
import pytest

# Read from env var so the base URL is configurable (default: localhost:8000)
SERVICE_URL = os.environ.get("SERVICE_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def service_url():
    """Return the base URL of the running service."""
    return SERVICE_URL


@pytest.fixture(scope="module", autouse=True)
def wait_for_service(service_url, timeout=600):
    """
    Block until the service /health endpoint responds with 200.

    Uses a generous timeout (default 600 s) because the first request may
    trigger a model download in the container's startup sequence.
    """
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{service_url}/health", timeout=5)
            if r.status_code == 200:
                return
            last_error = f"status {r.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(2)
    pytest.fail(f"Service at {service_url} not ready after {timeout}s (last error: {last_error})")
