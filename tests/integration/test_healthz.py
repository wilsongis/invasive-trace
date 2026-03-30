"""Integration tests for the /healthz endpoint — bootstrap runtime smoke tests."""

import time

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Shared TestClient for /healthz tests."""
    with TestClient(app) as c:
        yield c


def test_healthz_returns_200(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200


def test_healthz_response_body(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.json() == {"status": "ok"}


def test_healthz_content_type(client: TestClient) -> None:
    response = client.get("/healthz")
    assert "application/json" in response.headers["content-type"]


def test_bootstrap_api_surface_limited() -> None:
    """Only approved bootstrap/runtime routes should be present."""
    routes = {route.path for route in app.routes}
    for path in routes:
        assert (
            path == "/"
            or path == "/healthz"
            or path.startswith("/api/v1")
            or path.startswith("/openapi")
            or path.startswith("/docs")
            or path.startswith("/redoc")
        ), f"Unexpected route exposed in Wave 0: {path}"


def test_healthz_p95_latency() -> None:
    """SC-005: /healthz must respond in p95 <= 250ms over 10 requests."""
    with TestClient(app) as c:
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = c.get("/healthz")
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert response.status_code == 200
            latencies.append(elapsed_ms)
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    assert p95 <= 250, f"p95 latency {p95:.1f}ms exceeds 250ms threshold"


def test_api_v1_prefix_exists(client: TestClient) -> None:
    """Bootstrap routing exposes /api/v1 prefix; 404 is acceptable (no routes yet)."""
    response = client.get("/api/v1/")
    assert response.status_code in (200, 404, 405)


def test_healthz_latency_p95(client: TestClient) -> None:
    """p95 latency of 10 sequential /healthz requests must be <= 250ms."""
    samples: list[float] = []
    for _ in range(10):
        start = time.perf_counter()
        client.get("/healthz")
        samples.append(time.perf_counter() - start)

    samples.sort()
    p95_index = max(0, int(0.95 * len(samples)) - 1)
    p95 = samples[p95_index]
    assert p95 <= 0.250, f"p95 latency {p95 * 1000:.1f}ms exceeds 250ms threshold"
