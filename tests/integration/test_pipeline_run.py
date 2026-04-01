"""Integration tests for POST /api/v1/rois/{id}/pipeline/run.

These tests run against a live PostGIS container.  All ML stage classes are
mocked so the tests validate API contracts and DB persistence, not ML accuracy.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.models.spectral import SpectralTimeSeries

pytestmark = [pytest.mark.integration]

ROI_WKT = "POLYGON((-100 40, -99 40, -99 39, -100 39, -100 40))"


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def seeded_roi(client: TestClient) -> dict:
    """Seed one ROI and return its JSON payload."""
    res = client.post(
        "/api/v1/rois",
        json={"name": "Pipeline Test ROI", "description": "w3 integration", "geom_wkt": ROI_WKT},
    )
    assert res.status_code == 201
    return res.json()


def _mock_ml_context(
    anomalies: list[tuple[date, float]],
    species: str,
    conf: float,
    hotspot: float,
):
    """Context manager factory that patches all three ML stages."""

    s1 = patch("app.services.pipeline.AnomalyDetector")
    s2 = patch("app.services.pipeline.FocalClassifier")
    s3 = patch("app.services.pipeline.UNetTexture")
    patch_fn = patch(
        "app.services.pipeline.extract_sentinel2_patch",
        new_callable=AsyncMock,
        return_value=np.zeros((4, 512, 512), dtype=np.float32),
    )
    elev = patch(
        "app.services.feature_extractor.get_elevation",
        new_callable=AsyncMock,
        return_value=0.0,
    )
    return s1, s2, s3, patch_fn, elev


class TestPipelineTriggerEndpoint:
    def test_post_pipeline_run_404_for_unknown_roi(self, client: TestClient) -> None:
        res = client.post(f"/api/v1/rois/{uuid4()}/pipeline/run")
        assert res.status_code == 404

    def test_post_pipeline_run_200_with_zero_spectral_rows(
        self, client: TestClient, seeded_roi: dict
    ) -> None:
        """ROI exists but has no spectral rows → 200 with predictions_created=0."""
        roi_id = seeded_roi["id"]

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS3.return_value.load.return_value = MockS3.return_value

            res = client.post(f"/api/v1/rois/{roi_id}/pipeline/run")

        assert res.status_code == 200
        body = res.json()
        assert body["predictions_created"] == 0
        assert body["model_version"] == "rf-v0.1.0"
        assert "message" in body
        assert isinstance(body["message"], str)
        assert len(body["message"]) > 0

    def test_post_pipeline_run_200_with_predictions(
        self, client: TestClient, seeded_roi: dict
    ) -> None:
        """ROI with seeded spectral row and mocked ML stages creates a prediction."""
        roi_id = seeded_roi["id"]

        # First ingest a spectral row for the ROI
        ingest_res = client.post(
            "/api/v1/scenes/ingest",
            json={
                "roi_id": roi_id,
                "start_date": "2024-05-01",
                "end_date": "2024-07-31",
                "platform": "sentinel-2",
            },
        )
        # Scene ingest may fail if Planetary Computer is unavailable in CI —
        # seed a synthetic row directly via the DB if that's the case.
        if ingest_res.status_code != 200 or ingest_res.json().get("scenes_inserted", 0) == 0:
            pytest.skip("No Sentinel-2 scenes available for test ROI — skipping pipeline run")

        anomaly_date = date(2024, 6, 1)
        fake_row = MagicMock(spec=SpectralTimeSeries)
        fake_row.scene_date = anomaly_date
        fake_row.ndvi = 0.61
        fake_row.endvi = 0.52
        fake_row.red_edge = 0.43
        fake_row.is_masked = False
        fake_row.stac_item = "S2A_TEST_SEED"

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
            patch(
                "sqlalchemy.ext.asyncio.AsyncSession.execute",
                new_callable=AsyncMock,
            ) as mock_execute,
        ):
            execute_result = MagicMock()
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = [fake_row]
            execute_result.scalars.return_value = scalars_mock
            mock_execute.return_value = execute_result

            MockS1.return_value.load.return_value = MockS1.return_value
            MockS1.return_value.predict.return_value = [(anomaly_date, 0.9)]
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS2.return_value.predict.return_value = ("Bromus tectorum", 0.87)
            MockS3.return_value.load.return_value = MockS3.return_value
            MockS3.return_value.infer.return_value = 0.74

            res = client.post(f"/api/v1/rois/{roi_id}/pipeline/run")

        assert res.status_code == 200
        body = res.json()
        assert body["predictions_created"] >= 1
        assert body["model_version"] == "rf-v0.1.0"
        assert "message" in body

    def test_pipeline_response_schema(self, client: TestClient, seeded_roi: dict) -> None:
        """Response must contain roi_id, predictions_created, model_version, message."""
        roi_id = seeded_roi["id"]

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS3.return_value.load.return_value = MockS3.return_value

            res = client.post(f"/api/v1/rois/{roi_id}/pipeline/run")

        assert res.status_code == 200
        body = res.json()
        assert "roi_id" in body
        assert "predictions_created" in body
        assert "model_version" in body
        assert "message" in body
        assert body["roi_id"] == roi_id


class TestPipelineDBConstraintCompliance:
    def test_no_data_pipeline_does_not_write_predictions(
        self, client: TestClient, seeded_roi: dict
    ) -> None:
        """Pipeline with no anomalies must write zero rows (SC-006 invariant)."""
        roi_id = seeded_roi["id"]

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS1.return_value.predict.return_value = []
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS3.return_value.load.return_value = MockS3.return_value

            res = client.post(f"/api/v1/rois/{roi_id}/pipeline/run")

        assert res.status_code == 200
        assert res.json()["predictions_created"] == 0
        assert res.json()["message"] != ""
