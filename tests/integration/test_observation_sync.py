"""Integration tests for ROI-scoped observation sync endpoint."""

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


def _create_roi(client: TestClient) -> str:
    payload = {
        "name": "Sync ROI",
        "description": "integration-test",
        "geom_wkt": "POLYGON((-100 40, -99 40, -99 39, -100 39, -100 40))",
    }
    response = client.post("/api/v1/rois", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_observation_sync_requires_existing_roi(client: TestClient) -> None:
    response = client.post(
        "/api/v1/observations/sync",
        json={"roi_id": "00000000-0000-0000-0000-000000000000", "taxon_ids": []},
    )
    assert response.status_code == 404
    detail = response.json().get("detail", {})
    assert detail.get("code") == "ROI_NOT_FOUND"


def test_observation_sync_returns_summary_shape(client: TestClient) -> None:
    roi_id = _create_roi(client)
    response = client.post(
        "/api/v1/observations/sync",
        json={"roi_id": roi_id, "taxon_ids": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert "sources_polled" in body
    assert "records_inserted" in body
    assert "records_skipped" in body
