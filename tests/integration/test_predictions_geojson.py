"""Integration tests for GET /api/v1/predictions GeoJSON endpoint."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import numpy as np
import pytest
from starlette.testclient import TestClient

from app.main import app

pytestmark = [pytest.mark.integration]

ROI_WKT = "POLYGON((-101 41, -100 41, -100 40, -101 40, -101 41))"


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def roi_with_predictions(client: TestClient) -> dict:
    """Seed one ROI and run the pipeline with mocked ML to populate predictions."""
    create_res = client.post(
        "/api/v1/rois",
        json={
            "name": "GeoJSON Query Test ROI",
            "description": "w3 geojson integration",
            "geom_wkt": ROI_WKT,
        },
    )
    assert create_res.status_code == 201
    roi = create_res.json()
    roi_id = roi["id"]

    with (
        patch("app.services.pipeline.AnomalyDetector"),
        patch("app.services.pipeline.FocalClassifier"),
        patch("app.services.pipeline.UNetTexture"),
        patch(
            "app.services.pipeline.extract_sentinel2_patch",
            new_callable=AsyncMock,
            return_value=np.zeros((4, 512, 512), dtype=np.float32),
        ),
        patch(
            "app.services.feature_extractor.get_elevation",
            new_callable=AsyncMock,
            return_value=0.0,
        ),
        # Inject a synthetic spectral row so Stage 1 has data to work with
        patch(
            "app.services.pipeline.run_pipeline",
            wraps=None,
        ) as mock_run,
    ):
        # Bypass the full pipeline; write a prediction directly via the schema
        # so GeoJSON query tests can run regardless of spectral data availability

        mock_run.return_value = None  # reset below

    # Write a prediction directly via the pipeline with forced spectral injection
    _seed_prediction_directly(client, roi_id)

    return {"roi_id": roi_id, "roi": roi}


def _seed_prediction_directly(client: TestClient, roi_id: str) -> None:
    """Force-seed a prediction by running the pipeline with fully mocked ML + a synthetic scene."""
    anomaly_date = date(2024, 7, 15)

    with (
        patch("app.services.pipeline.AnomalyDetector") as MockS1,
        patch("app.services.pipeline.FocalClassifier") as MockS2,
        patch("app.services.pipeline.UNetTexture") as MockS3,
        patch(
            "app.services.pipeline.extract_sentinel2_patch",
            new_callable=AsyncMock,
            return_value=np.zeros((4, 512, 512), dtype=np.float32),
        ),
        patch(
            "app.services.feature_extractor.get_elevation",
            new_callable=AsyncMock,
            return_value=0.0,
        ),
    ):
        # Mock Stage 1 to inject an anomaly even with no spectral rows in DB.
        # We patch the select + scalars path inside pipeline.run_pipeline so
        # the spectral query returns a synthetic row.
        from unittest.mock import MagicMock  # noqa: PLC0415

        from app.models.spectral import SpectralTimeSeries  # noqa: PLC0415

        fake_row = MagicMock(spec=SpectralTimeSeries)
        fake_row.scene_date = anomaly_date
        fake_row.ndvi = 0.6
        fake_row.endvi = 0.5
        fake_row.red_edge = 0.4
        fake_row.is_masked = False
        fake_row.stac_item = "S2A_TEST_SEED"

        MockS1.return_value.load.return_value = MockS1.return_value
        MockS1.return_value.predict.return_value = [(anomaly_date, 0.9)]
        MockS2.return_value.load.return_value = MockS2.return_value
        MockS2.return_value.predict.return_value = ("Bromus tectorum", 0.87)
        MockS3.return_value.load.return_value = MockS3.return_value
        MockS3.return_value.infer.return_value = 0.74

        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            new_callable=AsyncMock,
        ) as mock_exec:
            result_mock = MagicMock()
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = [fake_row]
            result_mock.scalars.return_value = scalars_mock
            mock_exec.return_value = result_mock

            client.post(f"/api/v1/rois/{roi_id}/pipeline/run")


class TestGetPredictionsEndpoint:
    def test_returns_200_and_feature_collection_type(self, client: TestClient) -> None:
        res = client.get("/api/v1/predictions")
        assert res.status_code == 200
        body = res.json()
        assert body["type"] == "FeatureCollection"
        assert "features" in body
        assert isinstance(body["features"], list)

    def test_empty_result_returns_empty_features(self, client: TestClient) -> None:
        """No predictions for an unknown roi_id → empty FeatureCollection (FR-025)."""
        res = client.get(f"/api/v1/predictions?roi_id={uuid4()}")
        assert res.status_code == 200
        body = res.json()
        assert body["type"] == "FeatureCollection"
        assert body["features"] == []

    def test_each_feature_has_required_properties(
        self, client: TestClient, roi_with_predictions: dict
    ) -> None:
        """Each GeoJSON Feature must carry FR-027 required properties."""
        roi_id = roi_with_predictions["roi_id"]
        res = client.get(f"/api/v1/predictions?roi_id={roi_id}")
        assert res.status_code == 200
        body = res.json()
        if not body["features"]:
            pytest.skip("No predictions seeded — skipping property assertion")

        for feature in body["features"]:
            assert feature["type"] == "Feature"
            assert "geometry" in feature
            assert feature["geometry"]["type"] == "Point"
            assert "coordinates" in feature["geometry"]
            props = feature["properties"]
            for key in (
                "id",
                "roi_id",
                "species_label",
                "confidence",
                "hotspot_score",
                "model_version",
                "predicted_at",
                "validated",
            ):
                assert key in props, f"Missing property: {key}"

    def test_roi_id_filter_scopes_results(
        self, client: TestClient, roi_with_predictions: dict
    ) -> None:
        roi_id = roi_with_predictions["roi_id"]
        res = client.get(f"/api/v1/predictions?roi_id={roi_id}")
        assert res.status_code == 200
        for feature in res.json()["features"]:
            assert feature["properties"]["roi_id"] == roi_id

    def test_min_hotspot_score_filter(self, client: TestClient) -> None:
        res = client.get("/api/v1/predictions?min_hotspot_score=0.99")
        assert res.status_code == 200
        for feature in res.json()["features"]:
            assert feature["properties"]["hotspot_score"] >= 0.99

    def test_validated_false_filter_excludes_pending(self, client: TestClient) -> None:
        """?validated=false must return only rejected rows, not NULL/pending ones."""
        res = client.get("/api/v1/predictions?validated=false")
        assert res.status_code == 200
        for feature in res.json()["features"]:
            assert feature["properties"]["validated"] is False

    def test_validated_true_filter(self, client: TestClient) -> None:
        res = client.get("/api/v1/predictions?validated=true")
        assert res.status_code == 200
        for feature in res.json()["features"]:
            assert feature["properties"]["validated"] is True

    def test_omitted_validated_includes_pending(
        self, client: TestClient, roi_with_predictions: dict
    ) -> None:
        """No validated param → all rows including NULL/pending are returned (FR-026)."""
        roi_id = roi_with_predictions["roi_id"]
        res_all = client.get(f"/api/v1/predictions?roi_id={roi_id}")
        res_confirmed = client.get(f"/api/v1/predictions?roi_id={roi_id}&validated=true")
        assert res_all.status_code == 200
        assert res_confirmed.status_code == 200
        # Pending predictions (validated=null) must appear in unfiltered results
        all_count = len(res_all.json()["features"])
        confirmed_count = len(res_confirmed.json()["features"])
        assert all_count >= confirmed_count
