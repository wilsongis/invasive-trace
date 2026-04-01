"""Unit tests for Stage 1 — AnomalyDetector (anomaly-v0.1.0)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from app.ml.stage1_anomaly import (
    ARTIFACT_PATH,
    AnomalyDetector,
    AnomalyDetectorArtifactMissingError,
)


def _make_ndvi_series(n: int = 24, anomaly_index: int = 20) -> list[tuple[date, float]]:
    """Generate a synthetic NDVI time series with one planted anomaly."""
    base = date(2024, 1, 1)
    rng = np.random.default_rng(42)
    vals = [(base + timedelta(days=14 * i), float(rng.uniform(0.4, 0.7))) for i in range(n)]
    # Plant a clear anomaly
    d, _ = vals[anomaly_index]
    vals[anomaly_index] = (d, 0.95)
    return vals


class TestAnomalyDetectorFitPredict:
    def test_fit_returns_self(self) -> None:
        series = _make_ndvi_series()
        detector = AnomalyDetector()
        result = detector.fit(series)
        assert result is detector

    def test_predict_returns_list_of_tuples(self) -> None:
        series = _make_ndvi_series()
        detector = AnomalyDetector()
        detector.fit(series)
        anomalies = detector.predict(series)
        assert isinstance(anomalies, list)
        for item in anomalies:
            assert isinstance(item, tuple)
            scene_date, score = item
            assert isinstance(scene_date, date)
            assert isinstance(score, float)
            assert score >= 0.0, "departure_score must be non-negative for flagged scenes"

    def test_predict_detects_planted_anomaly(self) -> None:
        anomaly_index = 20
        series = _make_ndvi_series(anomaly_index=anomaly_index)
        planted_date = series[anomaly_index][0]
        detector = AnomalyDetector()
        detector.fit(series)
        anomalies = detector.predict(series)
        detected_dates = {d for d, _ in anomalies}
        assert planted_date in detected_dates

    def test_predict_empty_series_returns_empty(self) -> None:
        series = _make_ndvi_series()
        detector = AnomalyDetector()
        detector.fit(series)
        assert detector.predict([]) == []

    def test_fit_raises_on_empty_series(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            AnomalyDetector().fit([])

    def test_predict_before_fit_raises(self) -> None:
        with pytest.raises(RuntimeError):
            AnomalyDetector().predict(_make_ndvi_series())

    def test_fit_season_window_filters_dates(self) -> None:
        series = _make_ndvi_series(n=36)
        start = series[0][0]
        end = series[11][0]
        detector = AnomalyDetector()
        # Should not raise even though we are using a narrow window
        detector.fit(series, season_start=start, season_end=end)
        assert detector._model is not None


class TestAnomalyDetectorArtifact:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        series = _make_ndvi_series()
        detector = AnomalyDetector()
        detector.fit(series)

        artifact = tmp_path / "model.joblib"
        with patch.object(AnomalyDetector, "ARTIFACT_PATH", artifact):
            detector.ARTIFACT_PATH = artifact
            detector.save()
            assert artifact.exists()

            loaded = AnomalyDetector()
            loaded.ARTIFACT_PATH = artifact
            loaded.load()
            assert loaded._model is not None

    def test_load_raises_when_artifact_missing(self, tmp_path: Path) -> None:
        """Fail-fast: missing artifact must raise before any DB write (W3-T007)."""
        missing = tmp_path / "nonexistent.joblib"
        detector = AnomalyDetector()
        detector.ARTIFACT_PATH = missing
        with pytest.raises(AnomalyDetectorArtifactMissingError):
            detector.load()

    def test_artifact_path_matches_registry(self) -> None:
        assert str(ARTIFACT_PATH) == "models/AnomalyDetector/anomaly-v0.1.0/model.joblib"

    def test_version_string_matches_registry(self) -> None:
        assert AnomalyDetector.VERSION == "anomaly-v0.1.0"
