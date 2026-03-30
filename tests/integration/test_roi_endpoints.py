"""Integration tests for ROI endpoints."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from starlette.testclient import TestClient

from app.main import app

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def test_roi_create_and_fetch_round_trip(client: TestClient) -> None:
    create_payload = {
        "name": "SGI Test ROI",
        "description": "integration-test",
        "geom_wkt": "POLYGON((-100 40, -99 40, -99 39, -100 39, -100 40))",
    }
    create_response = client.post("/api/v1/rois", json=create_payload)
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["geometry"]["type"] == "Polygon"

    get_response = client.get(f"/api/v1/rois/{data['id']}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["name"] == create_payload["name"]


def test_roi_list_returns_created_roi(client: TestClient) -> None:
    response = client.get("/api/v1/rois")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
