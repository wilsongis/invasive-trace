"""Stage 1 — AnomalyDetector (anomaly-v0.1.0).

IsolationForest on NDVI time series for seasonal green-up departure detection.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

VERSION = "anomaly-v0.1.0"
ARTIFACT_PATH = Path("models/AnomalyDetector/anomaly-v0.1.0/model.joblib")
CONTAMINATION = 0.1


class AnomalyDetectorArtifactMissingError(FileNotFoundError):
    """Raised when the Stage 1 artifact is absent at the registered path."""


class AnomalyDetector:
    """IsolationForest-based NDVI seasonal anomaly detector.

    Training API : fit(ndvi_series, season_start, season_end)
    Inference API: predict(ndvi_series)
    Load API     : load()
    """

    VERSION = VERSION
    ARTIFACT_PATH = ARTIFACT_PATH

    def __init__(self) -> None:
        self._model: IsolationForest | None = None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        ndvi_series: list[tuple[date, float]],
        season_start: date | None = None,
        season_end: date | None = None,
    ) -> AnomalyDetector:
        """Train on an NDVI time series, optionally restricted to a season window.

        Args:
            ndvi_series: List of (scene_date, ndvi) tuples (unmasked rows only).
            season_start: Optional inclusive window start.
            season_end: Optional inclusive window end.

        Returns:
            self (for method chaining).
        """
        if season_start is not None and season_end is not None:
            ndvi_series = [(d, v) for d, v in ndvi_series if season_start <= d <= season_end]

        if not ndvi_series:
            raise ValueError("Cannot fit AnomalyDetector on empty NDVI series")

        vals = np.array([v for _, v in ndvi_series], dtype=np.float32).reshape(-1, 1)
        self._model = IsolationForest(contamination=CONTAMINATION, random_state=42)
        self._model.fit(vals)
        logger.info("stage1_fit version=%s n_samples=%d", self.VERSION, len(vals))
        return self

    def save(self) -> None:
        """Serialise the fitted model to the registered artifact path."""
        if self._model is None:
            raise RuntimeError("Cannot save an unfitted AnomalyDetector")
        self.ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, self.ARTIFACT_PATH)
        logger.info("stage1_saved path=%s", self.ARTIFACT_PATH)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, ndvi_series: list[tuple[date, float]]) -> list[tuple[date, float]]:
        """Identify anomalous scenes in an NDVI time series.

        Args:
            ndvi_series: List of (scene_date, ndvi) tuples to score.

        Returns:
            List of (scene_date, departure_score) for scenes flagged as anomalous.
            departure_score is positive; higher values indicate stronger anomalies.
        """
        if self._model is None:
            raise RuntimeError("AnomalyDetector must be fitted or loaded before predict()")

        if not ndvi_series:
            return []

        vals = np.array([v for _, v in ndvi_series], dtype=np.float32).reshape(-1, 1)
        # decision_function: lower (more negative) = more anomalous → negate
        scores = -self._model.decision_function(vals)
        labels = self._model.predict(vals)  # -1 = anomaly, 1 = inlier

        results: list[tuple[date, float]] = [
            (scene_date, float(score))
            for (scene_date, _), score, label in zip(ndvi_series, scores, labels, strict=False)
            if label == -1
        ]

        logger.info(
            "stage1_predict version=%s n_input=%d n_anomalies=%d",
            self.VERSION,
            len(ndvi_series),
            len(results),
        )
        return results

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self) -> AnomalyDetector:
        """Load the model artifact. Raises AnomalyDetectorArtifactMissingError if absent.

        This check occurs before any DB interaction (fail-fast contract).
        """
        if not self.ARTIFACT_PATH.exists():
            raise AnomalyDetectorArtifactMissingError(
                f"Stage 1 artifact missing: {self.ARTIFACT_PATH}. "
                "Run app/scripts/train_anomaly.py to generate it."
            )
        self._model = joblib.load(self.ARTIFACT_PATH)
        logger.info("stage1_loaded version=%s path=%s", self.VERSION, self.ARTIFACT_PATH)
        return self
