"""Stage 2 — AlphaEarth Benchmark Classifier (alphaearth-benchmark-v0.1.0).

Experimental RandomForest wrapper that uses AlphaEarth annual 64-dimensional
embeddings as the feature vector instead of the baseline spectral indices.

This module is BENCHMARK-ONLY and MUST NOT replace the production
FocalClassifier (rf-v0.1.0) without a separate amendment backed by
benchmark evidence.
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)

VERSION = "alphaearth-benchmark-v0.1.0"
ARTIFACT_PATH = Path("models/AlphaEarthBenchmark/alphaearth-benchmark-v0.1.0/model.joblib")
EMBEDDING_DIM = 64


class AlphaEarthBenchmarkArtifactMissingError(FileNotFoundError):
    """Raised when the benchmark artifact is absent at the registered path."""


class AlphaEarthStage2Benchmark:
    """Experimental Stage 2 classifier using AlphaEarth embeddings.

    Feature vector: 64-dimensional AlphaEarth annual embedding.

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

    def fit(self, X: np.ndarray, y: list[str]) -> AlphaEarthStage2Benchmark:
        """Train on AlphaEarth embedding features.

        Args:
            X: Feature matrix of shape (n_samples, 64).
            y: Species label strings.

        Returns:
            self (for method chaining).
        """
        if len(X) == 0:
            raise ValueError("Cannot fit AlphaEarthStage2Benchmark on empty training set")

        if X.shape[1] != EMBEDDING_DIM:
            raise ValueError(f"Expected {EMBEDDING_DIM}-dim embeddings, got {X.shape[1]}")

        self._model = RandomForestClassifier(n_estimators=100, random_state=42)
        self._model.fit(X, y)
        logger.info(
            "alphaearth_benchmark_fit version=%s n_samples=%d n_classes=%d",
            self.VERSION,
            len(X),
            len(set(y)),
        )
        return self

    def save(self) -> None:
        """Serialise the fitted model to the registered artifact path."""
        if self._model is None:
            raise RuntimeError("Cannot save an unfitted AlphaEarthStage2Benchmark")
        self.ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, self.ARTIFACT_PATH)
        logger.info("alphaearth_benchmark_saved path=%s", self.ARTIFACT_PATH)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, X: np.ndarray) -> tuple[str, float]:
        """Classify using AlphaEarth embeddings.

        Args:
            X: Feature array of shape (1, 64) or (64,).

        Returns:
            Tuple of (species_label, confidence).
        """
        if self._model is None:
            raise RuntimeError(
                "AlphaEarthStage2Benchmark must be fitted or loaded before predict()"
            )

        X_arr = np.atleast_2d(X)
        label: str = self._model.predict(X_arr)[0]
        proba = self._model.predict_proba(X_arr)[0]
        confidence = float(np.max(proba))

        return label, confidence

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self) -> AlphaEarthStage2Benchmark:
        """Load the model artifact. Raises AlphaEarthBenchmarkArtifactMissingError."""
        if not self.ARTIFACT_PATH.exists():
            raise AlphaEarthBenchmarkArtifactMissingError(
                f"AlphaEarth benchmark artifact missing: {self.ARTIFACT_PATH}. "
                "Run the benchmark workflow to generate it."
            )
        self._model = joblib.load(self.ARTIFACT_PATH)
        logger.info(
            "alphaearth_benchmark_loaded version=%s path=%s",
            self.VERSION,
            self.ARTIFACT_PATH,
        )
        return self
