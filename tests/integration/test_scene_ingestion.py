"""Integration tests for scenes ingestion and retrieval endpoints."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace

import numpy as np
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.stac_client import StacQueryUnavailableError

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def _create_roi(client: TestClient) -> str:
    payload = {
        "name": "Scene Ingestion ROI",
        "description": "integration-test",
        "geom_wkt": "POLYGON((-104.5 40.0, -104.4 40.0, -104.4 40.1, -104.5 40.1, -104.5 40.0))",
    }
    response = client.post("/api/v1/rois", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _fake_scene(
    item_id: str,
    dt: datetime | None = None,
    missing_assets: bool = False,
) -> SimpleNamespace:
    scene_dt = dt or datetime(2024, 5, 10, tzinfo=UTC)
    assets = {
        "B03": SimpleNamespace(href=f"memory://{item_id}-B03.tif"),
        "B04": SimpleNamespace(href=f"memory://{item_id}-B04.tif"),
        "B05": SimpleNamespace(href=f"memory://{item_id}-B05.tif"),
        "B08": SimpleNamespace(href=f"memory://{item_id}-B08.tif"),
        "B8A": SimpleNamespace(href=f"memory://{item_id}-B8A.tif"),
        "QA60": SimpleNamespace(href=f"memory://{item_id}-QA60.tif"),
    }
    if missing_assets:
        assets.pop("B08")

    return SimpleNamespace(
        id=item_id,
        assets=assets,
        datetime=scene_dt,
        properties={"datetime": scene_dt.isoformat()},
    )


def test_scene_ingestion_happy_path_and_query_filters(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roi_id = _create_roi(client)

    async def fake_query_scenes(**kwargs):
        assert kwargs["platform"] == "sentinel-2"
        return [
            _fake_scene("scene-clean", datetime(2024, 5, 10, tzinfo=UTC)),
            _fake_scene("scene-masked", datetime(2024, 5, 12, tzinfo=UTC)),
        ]

    def fake_read_band_window(href: str, roi_bounds):
        return np.full((2, 2), 0.6, dtype=np.float32)

    monkeypatch.setattr("app.services.scene_ingestion.stac_client.query_scenes", fake_query_scenes)
    monkeypatch.setattr(
        "app.services.scene_ingestion.cloud_mask.compute_cloud_fraction",
        lambda href, bounds: (0.35, True) if href and "scene-masked" in href else (0.05, False),
    )
    monkeypatch.setattr(
        "app.services.scene_ingestion.indices.read_band_window",
        fake_read_band_window,
    )

    response = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": roi_id,
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
            "platform": "sentinel-2",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenes_queried"] == 2
    assert body["scenes_inserted"] == 2
    assert body["scenes_masked"] == 1
    assert body["scenes_skipped"] == 0

    list_response = client.get(f"/api/v1/scenes?roi_id={roi_id}&include_masked=true")
    assert list_response.status_code == 200
    records = list_response.json()
    assert len(records) == 2
    assert records[0]["scene_date"] == "2024-05-10"
    assert records[1]["scene_date"] == "2024-05-12"
    assert records[0]["scene_date"] <= records[1]["scene_date"]

    filtered = client.get(f"/api/v1/scenes?roi_id={roi_id}")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1


def test_scene_ingestion_validation_and_roi_not_found(client: TestClient) -> None:
    malformed_roi = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": "not-a-uuid",
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
        },
    )
    assert malformed_roi.status_code == 422

    bad_window = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": "00000000-0000-0000-0000-000000000000",
            "start_date": "2024-06-01",
            "end_date": "2024-05-01",
        },
    )
    assert bad_window.status_code == 422

    bad_platform = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": "00000000-0000-0000-0000-000000000000",
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
            "platform": "landsat-hls",
        },
    )
    assert bad_platform.status_code == 422

    missing_roi = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": "00000000-0000-0000-0000-000000000000",
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
        },
    )
    assert missing_roi.status_code == 404


def test_scene_ingestion_idempotency_and_skip_behavior(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roi_id = _create_roi(client)

    async def fake_query_scenes(**kwargs):
        return [
            _fake_scene("scene-repeat", datetime(2024, 5, 15, tzinfo=UTC)),
            _fake_scene(
                "scene-skip",
                datetime(2024, 5, 16, tzinfo=UTC),
                missing_assets=True,
            ),
        ]

    monkeypatch.setattr("app.services.scene_ingestion.stac_client.query_scenes", fake_query_scenes)
    monkeypatch.setattr(
        "app.services.scene_ingestion.cloud_mask.compute_cloud_fraction",
        lambda href, bounds: (0.01, False),
    )
    monkeypatch.setattr(
        "app.services.scene_ingestion.indices.read_band_window",
        lambda href, bounds: np.full((2, 2), 0.7, dtype=np.float32),
    )

    payload = {
        "roi_id": roi_id,
        "start_date": "2024-05-01",
        "end_date": "2024-05-31",
        "platform": "sentinel-2",
    }

    first = client.post("/api/v1/scenes/ingest", json=payload)
    assert first.status_code == 200
    assert first.json()["scenes_inserted"] == 1
    assert first.json()["scenes_skipped"] == 1

    second = client.post("/api/v1/scenes/ingest", json=payload)
    assert second.status_code == 200
    assert second.json()["scenes_inserted"] == 0
    assert second.json()["scenes_updated"] == 1
    assert second.json()["scenes_skipped"] == 1


def test_scene_ingestion_terminal_stac_unavailability(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roi_id = _create_roi(client)

    async def unavailable(**kwargs):
        raise StacQueryUnavailableError("down")

    monkeypatch.setattr("app.services.scene_ingestion.stac_client.query_scenes", unavailable)

    response = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": roi_id,
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
            "platform": "sentinel-2",
        },
    )

    assert response.status_code == 500


def test_scene_query_filters_by_date_window(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roi_id = _create_roi(client)

    async def fake_query_scenes(**kwargs):
        return [
            _fake_scene("scene-a", datetime(2024, 5, 1, tzinfo=UTC)),
            _fake_scene("scene-b", datetime(2024, 5, 20, tzinfo=UTC)),
            _fake_scene("scene-c", datetime(2024, 6, 1, tzinfo=UTC)),
        ]

    monkeypatch.setattr("app.services.scene_ingestion.stac_client.query_scenes", fake_query_scenes)
    monkeypatch.setattr(
        "app.services.scene_ingestion.cloud_mask.compute_cloud_fraction",
        lambda href, bounds: (0.05, False),
    )
    monkeypatch.setattr(
        "app.services.scene_ingestion.indices.read_band_window",
        lambda href, bounds: np.full((2, 2), 0.6, dtype=np.float32),
    )

    ingest = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": roi_id,
            "start_date": "2024-05-01",
            "end_date": "2024-06-30",
            "platform": "sentinel-2",
        },
    )
    assert ingest.status_code == 200

    filtered = client.get(
        f"/api/v1/scenes?roi_id={roi_id}&start_date=2024-05-10&end_date=2024-05-31"
    )
    assert filtered.status_code == 200
    records = filtered.json()
    assert len(records) == 1
    assert records[0]["stac_item"] == "scene-b"


def test_scene_latency_smoke_checks(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    roi_id = _create_roi(client)

    async def fake_query_scenes(**kwargs):
        return [_fake_scene("scene-latency", datetime(2024, 5, 17, tzinfo=UTC))]

    monkeypatch.setattr("app.services.scene_ingestion.stac_client.query_scenes", fake_query_scenes)
    monkeypatch.setattr(
        "app.services.scene_ingestion.cloud_mask.compute_cloud_fraction",
        lambda href, bounds: (0.01, False),
    )
    monkeypatch.setattr(
        "app.services.scene_ingestion.indices.read_band_window",
        lambda href, bounds: np.full((2, 2), 0.8, dtype=np.float32),
    )

    start_discovery = time.monotonic()
    asyncio.run(fake_query_scenes())
    discovery_elapsed = time.monotonic() - start_discovery
    assert discovery_elapsed <= 15.0

    start_ingest = time.monotonic()
    ingest_response = client.post(
        "/api/v1/scenes/ingest",
        json={
            "roi_id": roi_id,
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
            "platform": "sentinel-2",
        },
    )
    ingest_elapsed = time.monotonic() - start_ingest

    assert ingest_response.status_code == 200
    assert ingest_elapsed <= 60.0

    start_list = time.monotonic()
    list_response = client.get(f"/api/v1/scenes?roi_id={roi_id}")
    list_elapsed = time.monotonic() - start_list

    assert list_response.status_code == 200
    assert list_elapsed <= 2.0
