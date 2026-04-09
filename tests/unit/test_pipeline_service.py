"""Unit tests for the Wave 3 pipeline service (app/services/pipeline.py)."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from app.services.ml_runtime import STAGE2_VERSION, clamp_confidence, clamp_hotspot_score


class TestClampHelpers:
    def test_clamp_confidence_within_bounds(self) -> None:
        assert clamp_confidence(0.5) == 0.5
        assert clamp_confidence(0.0) == 0.0
        assert clamp_confidence(1.0) == 1.0

    def test_clamp_confidence_clips_above(self) -> None:
        assert clamp_confidence(1.5) == 1.0

    def test_clamp_confidence_clips_below(self) -> None:
        assert clamp_confidence(-0.1) == 0.0

    def test_clamp_hotspot_within_bounds(self) -> None:
        assert clamp_hotspot_score(0.74) == 0.74

    def test_clamp_hotspot_clips_above(self) -> None:
        assert clamp_hotspot_score(1.01) == 1.0

    def test_clamp_hotspot_clips_below(self) -> None:
        assert clamp_hotspot_score(-0.5) == 0.0


class TestPipelineStage2Version:
    def test_stage2_version_matches_registry(self) -> None:
        assert STAGE2_VERSION == "rf-v0.1.0"


class TestPipelineLineage:
    def test_sidecar_contains_all_three_versions(self, caplog) -> None:
        """Lineage log must include stage1, stage2, stage3 versions (FR-020)."""
        import logging  # noqa: PLC0415

        sidecar = {
            "roi_id": str(uuid4()),
            "predictions_created": 1,
            "stage1_version": "anomaly-v0.1.0",
            "stage2_version": "rf-v0.1.0",
            "stage3_version": "unet-v0.1.0",
        }
        with caplog.at_level(logging.INFO, logger="app.services.pipeline"):
            import logging as _log  # noqa: PLC0415

            _log.getLogger("app.services.pipeline").info("pipeline_lineage %s", json.dumps(sidecar))

        assert "anomaly-v0.1.0" in caplog.text
        assert "rf-v0.1.0" in caplog.text
        assert "unet-v0.1.0" in caplog.text


class TestPipelineRunOrchestration:
    """Verify orchestration logic using heavily mocked dependencies."""

    def _make_spectral_row(
        self,
        scene_date: date,
        ndvi: float = 0.6,
        is_masked: bool = False,
        stac_item: str = "S2A_TEST",
    ) -> MagicMock:
        row = MagicMock()
        row.scene_date = scene_date
        row.ndvi = ndvi
        row.endvi = 0.5
        row.red_edge = 0.4
        row.is_masked = is_masked
        row.stac_item = stac_item
        return row

    def _make_roi(self) -> MagicMock:
        from geoalchemy2.shape import from_shape  # noqa: PLC0415
        from shapely.geometry import Polygon  # noqa: PLC0415

        poly = Polygon([(-100, 40), (-99, 40), (-99, 39), (-100, 39), (-100, 40)])
        roi = MagicMock()
        roi.id = uuid4()
        roi.geom = from_shape(poly, srid=4326)
        return roi

    @pytest.mark.asyncio
    async def test_run_pipeline_returns_zero_when_no_spectral_rows(self) -> None:
        roi = self._make_roi()
        roi_id = roi.id

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=roi)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS3.return_value.load.return_value = MockS3.return_value

            from app.services.pipeline import run_pipeline  # noqa: PLC0415

            result = await run_pipeline(roi_id=roi_id, db=mock_db)

        assert result.predictions_created == 0
        assert result.model_version == "rf-v0.1.0"
        assert "No unmasked spectral data" in result.message

    @pytest.mark.asyncio
    async def test_run_pipeline_returns_zero_when_no_anomalies(self) -> None:
        roi = self._make_roi()
        roi_id = roi.id
        rows = [self._make_spectral_row(date(2024, 6, 1))]

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=roi)
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = rows
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        mock_db.execute = AsyncMock(return_value=execute_result)

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS1.return_value.predict.return_value = []  # no anomalies
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS3.return_value.load.return_value = MockS3.return_value

            from app.services.pipeline import run_pipeline  # noqa: PLC0415

            result = await run_pipeline(roi_id=roi_id, db=mock_db)

        assert result.predictions_created == 0
        assert "no anomalous scenes" in result.message.lower()

    @pytest.mark.asyncio
    async def test_run_pipeline_raises_for_missing_roi(self) -> None:
        from app.services.pipeline import ROINotFoundError, run_pipeline  # noqa: PLC0415

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS3.return_value.load.return_value = MockS3.return_value

            with pytest.raises(ROINotFoundError):
                await run_pipeline(roi_id=uuid4(), db=mock_db)

    @pytest.mark.asyncio
    async def test_model_version_on_written_prediction_is_stage2(self) -> None:
        """model_version col must store Stage 2 version only (FR-020, SC-004)."""
        roi = self._make_roi()
        roi_id = roi.id
        scene = date(2024, 6, 15)
        rows = [self._make_spectral_row(scene)]

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=roi)
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = rows
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        mock_db.execute = AsyncMock(return_value=execute_result)

        added_preds: list = []
        mock_db.add = MagicMock(side_effect=lambda obj: added_preds.append(obj))
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
            patch("app.services.pipeline.build_feature_vector", new_callable=AsyncMock) as MockFV,
            patch(
                "app.services.pipeline.extract_sentinel2_patch",
                new_callable=AsyncMock,
            ) as MockPatch,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS1.return_value.predict.return_value = [(scene, 0.8)]
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS2.return_value.predict.return_value = ("Bromus tectorum", 0.87)
            MockS3.return_value.load.return_value = MockS3.return_value
            MockS3.return_value.infer.return_value = 0.74
            MockFV.return_value = np.zeros((1, 4), dtype=np.float32)
            MockPatch.return_value = np.zeros((4, 512, 512), dtype=np.float32)

            from app.services.pipeline import run_pipeline  # noqa: PLC0415

            result = await run_pipeline(roi_id=roi_id, db=mock_db)

        assert result.predictions_created == 1
        assert result.model_version == "rf-v0.1.0"
        assert len(added_preds) == 1
        pred = added_preds[0]
        assert pred.model_version == "rf-v0.1.0"
        assert pred.validated is None
        assert 0.0 <= pred.confidence <= 1.0


# ---------------------------------------------------------------------------
# T012 — H3 regression guard: build_feature_vector is called per anomaly
# ---------------------------------------------------------------------------


class TestPipelineStage2FeatureVec:
    """Verify H3 fix: build_feature_vector is called once per Stage 1 anomaly."""

    def _make_roi(self) -> MagicMock:
        from geoalchemy2.shape import from_shape  # noqa: PLC0415
        from shapely.geometry import Polygon  # noqa: PLC0415

        poly = Polygon([(-100, 40), (-99, 40), (-99, 39), (-100, 39), (-100, 40)])
        roi = MagicMock()
        roi.id = uuid4()
        roi.geom = from_shape(poly, srid=4326)
        return roi

    def _make_spectral_row(
        self,
        scene_date: date = date(2024, 6, 15),
        ndvi: float = 0.6,
        stac_item: str = "S2A_TEST",
    ) -> MagicMock:
        row = MagicMock()
        row.scene_date = scene_date
        row.ndvi = ndvi
        row.endvi = 0.5
        row.red_edge = 0.4
        row.is_masked = False
        row.stac_item = stac_item
        return row

    @pytest.mark.asyncio
    async def test_pipeline_stage2_feature_vec_built(self) -> None:
        """build_feature_vector and stage2.predict are each called once per anomaly."""
        import numpy as np

        scene_date = date(2024, 6, 15)
        roi = self._make_roi()
        roi_id = roi.id
        scene = self._make_spectral_row(scene_date=scene_date)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=roi)
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [scene]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        mock_db.execute = AsyncMock(return_value=execute_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.pipeline.AnomalyDetector") as MockS1,
            patch("app.services.pipeline.FocalClassifier") as MockS2,
            patch("app.services.pipeline.UNetTexture") as MockS3,
            patch("app.services.pipeline.build_feature_vector", new_callable=AsyncMock) as MockFV,
            patch(
                "app.services.pipeline.extract_sentinel2_patch",
                new_callable=AsyncMock,
            ) as MockPatch,
        ):
            MockS1.return_value.load.return_value = MockS1.return_value
            MockS1.return_value.predict.return_value = [(scene_date, 0.8)]
            MockS2.return_value.load.return_value = MockS2.return_value
            MockS2.return_value.predict.return_value = ("Bromus tectorum", 0.87)
            MockS3.return_value.load.return_value = MockS3.return_value
            MockS3.return_value.infer.return_value = 0.74
            MockFV.return_value = np.zeros((1, 4), dtype=np.float32)
            MockPatch.return_value = np.zeros((4, 512, 512), dtype=np.float32)

            from app.services.pipeline import run_pipeline  # noqa: PLC0415

            await run_pipeline(roi_id=roi_id, db=mock_db)

        # H3 guard: build_feature_vector called once (per anomaly), passing spectral values
        MockFV.assert_called_once()
        call_kwargs = MockFV.call_args.kwargs
        assert "ndvi" in call_kwargs
        assert "lon" in call_kwargs

        # Stage 2 predict was called once with that feature vector
        MockS2.return_value.predict.assert_called_once()
