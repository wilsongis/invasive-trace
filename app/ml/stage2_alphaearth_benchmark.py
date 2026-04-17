"""Wave 1.5 benchmark Stage 2 wrapper for AlphaEarth-style embedding features."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

VERSION = "alphaearth-benchmark-v0.1.0"
ARTIFACT_PATH = Path("models/AlphaEarthStage2Benchmark/alphaearth-benchmark-v0.1.0/model.joblib")


class AlphaEarthBenchmarkArtifactMissingError(FileNotFoundError):
    """Raised when the benchmark artifact is absent at the registered path."""


class AlphaEarthStage2Benchmark:
    """Benchmark-only classifier using annual embedding vectors.

    This wrapper is experimental and must not replace the production Stage 2 baseline.
    """

    VERSION = VERSION
    ARTIFACT_PATH = ARTIFACT_PATH

    def __init__(self) -> None:
        self._model: RandomForestClassifier | None = None

    def fit(self, X: np.ndarray, y: list[str]) -> AlphaEarthStage2Benchmark:
        """Train the benchmark classifier on annual embedding vectors."""
        if len(X) == 0:
            raise ValueError("Cannot fit AlphaEarthStage2Benchmark on empty training set")

        self._model = RandomForestClassifier(n_estimators=200, random_state=42)
        self._model.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict labels for one or more embedding rows."""
        if self._model is None:
            raise RuntimeError(
                "AlphaEarthStage2Benchmark must be fitted or loaded before predict()"
            )
        return self._model.predict(np.atleast_2d(X))

    def save(self) -> None:
        """Serialize the fitted benchmark artifact to the registered path."""
        if self._model is None:
            raise RuntimeError("Cannot save an unfitted AlphaEarthStage2Benchmark")
        self.ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, self.ARTIFACT_PATH)

    def load(self) -> AlphaEarthStage2Benchmark:
        """Load benchmark artifact with fail-fast behavior when missing."""
        if not self.ARTIFACT_PATH.exists():
            raise AlphaEarthBenchmarkArtifactMissingError(
                f"Benchmark artifact missing: {self.ARTIFACT_PATH}. "
                "Run app/scripts/run_alphaearth_benchmark.py to generate evaluation artifacts."
            )
        self._model = joblib.load(self.ARTIFACT_PATH)
        return self
