"""Unit tests for Stage 2 — FocalClassifier (rf-v0.1.0)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.ml.stage2_classifier import (
    ARTIFACT_PATH,
    FocalClassifier,
    FocalClassifierArtifactMissingError,
)

_SPECIES = ["Bromus tectorum", "Tamarix ramosissima", "Centaurea solstitialis"]


def _make_dataset(n: int = 60) -> tuple[np.ndarray, list[str]]:
    rng = np.random.default_rng(7)
    X = rng.uniform(0.0, 1.0, (n, 4)).astype(np.float32)
    y = [_SPECIES[i % len(_SPECIES)] for i in range(n)]
    return X, y


class TestFocalClassifierFitPredict:
    def test_fit_returns_self(self) -> None:
        X, y = _make_dataset()
        clf = FocalClassifier()
        result = clf.fit(X, y)
        assert result is clf

    def test_predict_returns_label_and_confidence(self) -> None:
        X, y = _make_dataset()
        clf = FocalClassifier()
        clf.fit(X, y)
        label, conf = clf.predict(X[0])
        assert isinstance(label, str)
        assert label in _SPECIES
        assert 0.0 <= conf <= 1.0

    def test_predict_batch_input_shape(self) -> None:
        X, y = _make_dataset()
        clf = FocalClassifier()
        clf.fit(X, y)
        # 2D input (1, 4)
        label, conf = clf.predict(X[:1])
        assert isinstance(label, str)
        assert 0.0 <= conf <= 1.0

    def test_fit_raises_on_empty_dataset(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            FocalClassifier().fit(np.array([]).reshape(0, 4), [])

    def test_predict_before_fit_raises(self) -> None:
        X, _ = _make_dataset()
        with pytest.raises(RuntimeError):
            FocalClassifier().predict(X[0])


class TestFocalClassifierArtifact:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        X, y = _make_dataset()
        clf = FocalClassifier()
        clf.fit(X, y)

        artifact = tmp_path / "model.joblib"
        clf.ARTIFACT_PATH = artifact
        clf.save()
        assert artifact.exists()

        loaded = FocalClassifier()
        loaded.ARTIFACT_PATH = artifact
        loaded.load()
        label, conf = loaded.predict(X[0])
        assert isinstance(label, str)
        assert 0.0 <= conf <= 1.0

    def test_load_raises_when_artifact_missing(self, tmp_path: Path) -> None:
        """Fail-fast: missing artifact must raise before any DB write (W3-T007)."""
        missing = tmp_path / "nonexistent.joblib"
        clf = FocalClassifier()
        clf.ARTIFACT_PATH = missing
        with pytest.raises(FocalClassifierArtifactMissingError):
            clf.load()

    def test_artifact_path_matches_registry(self) -> None:
        assert str(ARTIFACT_PATH) == "models/FocalClassifier/rf-v0.1.0/model.joblib"

    def test_version_string_matches_registry(self) -> None:
        assert FocalClassifier.VERSION == "rf-v0.1.0"


class TestConfidenceRange:
    def test_confidence_within_0_1(self) -> None:
        """Confidence from predict() must be in [0.0, 1.0] since it's a probability."""
        X, y = _make_dataset(n=90)
        clf = FocalClassifier()
        clf.fit(X, y)
        for row in X:
            _, conf = clf.predict(row)
            assert 0.0 <= conf <= 1.0, f"confidence out of range: {conf}"
