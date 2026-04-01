"""Stage 2 — FocalClassifier (rf-v0.1.0).

RandomForest species-level classification on [ndvi, endvi, red_edge, elevation].
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)

VERSION = "rf-v0.1.0"
ARTIFACT_PATH = Path("models/FocalClassifier/rf-v0.1.0/model.joblib")


class FocalClassifierArtifactMissingError(FileNotFoundError):
    """Raised when the Stage 2 artifact is absent at the registered path."""


class FocalClassifier:
    """RandomForest invasive species classifier.

    Feature vector: [ndvi, endvi, red_edge, elevation]

    Training API : fit(X, y)
    Inference API: predict(X)
    Load API     : load()
    """

    VERSION = VERSION
    ARTIFACT_PATH = ARTIFACT_PATH

    def __init__(self) -> None:
        self._model: RandomForestClassifier | None = None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, X: np.ndarray, y: list[str]) -> FocalClassifier:
        """Train on feature matrix X with species label targets y.

        Args:
            X: Feature matrix of shape (n_samples, 4) — [ndvi, endvi, red_edge, elevation].
            y: Species label strings (e.g. "Bromus tectorum") sourced from
               ground_truth_observations.species_label (FR-012).

        Returns:
            self (for method chaining).
        """
        if len(X) == 0:
            raise ValueError("Cannot fit FocalClassifier on empty training set")

        self._model = RandomForestClassifier(n_estimators=100, random_state=42)
        self._model.fit(X, y)
        logger.info(
            "stage2_fit version=%s n_samples=%d n_classes=%d",
            self.VERSION,
            len(X),
            len(set(y)),
        )
        return self

    def save(self) -> None:
        """Serialise the fitted model to the registered artifact path."""
        if self._model is None:
            raise RuntimeError("Cannot save an unfitted FocalClassifier")
        self.ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, self.ARTIFACT_PATH)
        logger.info("stage2_saved path=%s", self.ARTIFACT_PATH)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, X: np.ndarray) -> tuple[str, float]:
        """Classify the feature vector; return (species_label, confidence).

        confidence is the max class probability from the RandomForest.
        Clamping to [0.0, 1.0] is the caller's responsibility before any DB write.

        Args:
            X: Feature array of shape (1, 4) or (4,) — [ndvi, endvi, red_edge, elevation].

        Returns:
            Tuple of (species_label, confidence).
        """
        if self._model is None:
            raise RuntimeError("FocalClassifier must be fitted or loaded before predict()")

        X_arr = np.atleast_2d(X)
        label: str = self._model.predict(X_arr)[0]
        proba = self._model.predict_proba(X_arr)[0]
        confidence = float(np.max(proba))

        return label, confidence

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self) -> FocalClassifier:
        """Load the model artifact. Raises FocalClassifierArtifactMissingError if absent.

        This check occurs before any DB interaction (fail-fast contract).
        """
        if not self.ARTIFACT_PATH.exists():
            raise FocalClassifierArtifactMissingError(
                f"Stage 2 artifact missing: {self.ARTIFACT_PATH}. "
                "Run app/scripts/train_classifier.py to generate it."
            )
        self._model = joblib.load(self.ARTIFACT_PATH)
        logger.info("stage2_loaded version=%s path=%s", self.VERSION, self.ARTIFACT_PATH)
        return self
