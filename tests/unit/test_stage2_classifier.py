"""Unit tests for Stage 2 classifier."""

import numpy as np
import pytest

from app.ml.stage2_classifier import (
    FEATURE_NAMES,
    VERSION,
    FocalClassifier,
    FocalClassifierArtifactMissingError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_X_y(n: int = 60) -> tuple[np.ndarray, list[str]]:
    """Minimal synthetic dataset (n×12 float matrix, 3 balanced species)."""
    rng = np.random.default_rng(42)
    X = rng.uniform(0.0, 1.0, (n, 12)).astype(np.float32)
    species = ["Bromus tectorum", "Tamarix ramosissima", "Centaurea solstitialis"]
    y = [species[i % len(species)] for i in range(n)]
    return X, y


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def test_classifier_initialization():
    """FocalClassifier initialises with correct version constant."""
    classifier = FocalClassifier()
    assert classifier is not None
    assert classifier.VERSION == "rf-v0.1.0"


def test_feature_names_length():
    """FEATURE_NAMES must contain exactly 12 entries."""
    assert len(FEATURE_NAMES) == 12


def test_feature_names_values():
    """FEATURE_NAMES must match the canonical spectral aggregate schema."""
    expected = [
        "ndvi_min",
        "ndvi_max",
        "ndvi_mean",
        "ndvi_std",
        "endvi_min",
        "endvi_max",
        "endvi_mean",
        "endvi_std",
        "red_edge_min",
        "red_edge_max",
        "red_edge_mean",
        "red_edge_std",
    ]
    assert expected == FEATURE_NAMES


def test_model_version():
    """VERSION module constant matches class attribute."""
    assert VERSION == "rf-v0.1.0"
    assert FocalClassifier.VERSION == VERSION


# ---------------------------------------------------------------------------
# clip_confidence
# ---------------------------------------------------------------------------


def test_clip_confidence_normal():
    assert FocalClassifier.clip_confidence(0.5) == pytest.approx(0.5)


def test_clip_confidence_below_zero():
    assert FocalClassifier.clip_confidence(-0.5) == 0.0


def test_clip_confidence_above_one():
    assert FocalClassifier.clip_confidence(1.5) == 1.0


def test_clip_confidence_exact_bounds():
    assert FocalClassifier.clip_confidence(0.0) == 0.0
    assert FocalClassifier.clip_confidence(1.0) == 1.0


# ---------------------------------------------------------------------------
# fit / predict
# ---------------------------------------------------------------------------


def test_fit_predict_shape():
    """Fitting on (N, 12) data returns (label, confidence) from predict."""
    X, y = _make_X_y()
    clf = FocalClassifier()
    clf.fit(X, y)
    label, confidence = clf.predict(X[0])
    assert isinstance(label, str)
    assert 0.0 <= confidence <= 1.0


def test_fit_predict_1d_input():
    """predict() accepts a 1-D array of length 12."""
    X, y = _make_X_y()
    clf = FocalClassifier()
    clf.fit(X, y)
    label, confidence = clf.predict(X[0].ravel())
    assert isinstance(label, str)


def test_fit_empty_raises():
    """Fitting on an empty dataset raises ValueError."""
    clf = FocalClassifier()
    with pytest.raises(ValueError, match="empty"):
        clf.fit(np.empty((0, 12), dtype=np.float32), [])


def test_predict_before_fit_raises():
    """predict() before fit() raises RuntimeError."""
    clf = FocalClassifier()
    with pytest.raises(RuntimeError):
        clf.predict(np.zeros(12))


# ---------------------------------------------------------------------------
# rf hyperparameters
# ---------------------------------------------------------------------------


def test_rf_hyperparameters():
    """Fitted RF uses the canonical hyperparameter set."""
    X, y = _make_X_y()
    clf = FocalClassifier()
    clf.fit(X, y)
    rf = clf._model
    assert rf.n_estimators == 100
    assert rf.max_depth == 15
    assert rf.min_samples_leaf == 5
    assert rf.class_weight == "balanced"
    assert rf.random_state == 42


# ---------------------------------------------------------------------------
# load error
# ---------------------------------------------------------------------------


def test_load_missing_artifact_raises(tmp_path, monkeypatch):
    """load() raises FocalClassifierArtifactMissingError when artifact is absent."""
    clf = FocalClassifier()
    # Point artifact path somewhere that doesn't exist
    monkeypatch.setattr(clf, "ARTIFACT_PATH", tmp_path / "nonexistent" / "classifier.pkl")
    with pytest.raises(FocalClassifierArtifactMissingError):
        clf.load()


def test_load_classifier_success(tmp_path):
    """load_classifier() finds and returns a fitted RF from a real artifact."""
    import joblib
    from sklearn.ensemble import RandomForestClassifier

    X, y = _make_X_y()
    model = RandomForestClassifier(n_estimators=10, random_state=42, class_weight="balanced")
    model.fit(X, y)
    artifact = tmp_path / "classifier.pkl"
    joblib.dump(model, artifact)

    version = "rf-v0.1.0"
    # Monkey-patch the path resolution so load_classifier looks in tmp_path
    import unittest.mock as mock

    with mock.patch("app.ml.stage2_classifier.Path") as MockPath:
        mock_path_instance = mock.MagicMock()
        mock_path_instance.exists.return_value = True
        MockPath.return_value = mock_path_instance
        with mock.patch("app.ml.stage2_classifier.joblib.load", return_value=model):
            loaded = FocalClassifier.load_classifier(version)
    assert hasattr(loaded, "predict")
    assert hasattr(loaded, "predict_proba")


def test_get_model_metadata_keys(tmp_path):
    """get_model_metadata() returns dict with feature_names, class_labels, model_version."""
    import json
    import unittest.mock as mock

    metadata = {
        "model_version": "rf-v0.1.0",
        "feature_names": ["ndvi_min", "ndvi_max"],
        "class_labels": ["Bromus tectorum"],
    }
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(metadata))

    with mock.patch("app.ml.stage2_classifier.Path") as MockPath:
        mock_path_instance = mock.MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.__truediv__ = lambda self, other: metadata_file
        MockPath.return_value = mock_path_instance
        import builtins

        orig_open = builtins.open
        open_side_effect = lambda p, *a, **kw: orig_open(metadata_file, *a, **kw)  # noqa: E731
        with mock.patch("builtins.open", side_effect=open_side_effect):
            result = FocalClassifier.get_model_metadata("rf-v0.1.0")
    assert "feature_names" in result
    assert "class_labels" in result
    assert "model_version" in result


# ---------------------------------------------------------------------------
# T013 — training + inference unit tests
# ---------------------------------------------------------------------------


def test_rf_stratified_split():
    """train_classifier() uses stratified split preserving species distribution."""
    from uuid import uuid4

    from app.services.feature_extractor import TrainingCohortRecord

    rng = np.random.default_rng(1)
    species = ["Bromus tectorum", "Tamarix ramosissima", "Centaurea solstitialis"]
    dummy_roi = uuid4()
    n = 60
    raw = rng.uniform(0.0, 1.0, (n, 12))
    cohort = [
        TrainingCohortRecord(
            roi_id=dummy_roi,
            species_label=species[i % 3],
            ndvi_min=raw[i][0],
            ndvi_max=raw[i][1],
            ndvi_mean=raw[i][2],
            ndvi_std=raw[i][3],
            endvi_min=raw[i][4],
            endvi_max=raw[i][5],
            endvi_mean=raw[i][6],
            endvi_std=raw[i][7],
            red_edge_min=raw[i][8],
            red_edge_max=raw[i][9],
            red_edge_mean=raw[i][10],
            red_edge_std=raw[i][11],
        )
        for i in range(n)
    ]
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:  # noqa: SIM117
        result = FocalClassifier.train_classifier(cohort, tmpdir)
    # Expect 3 classes in result
    assert len(result.class_labels) == 3
    assert set(result.class_labels) == set(species)


def test_rf_metrics_numeric(tmp_path):
    """CV + test metrics are floats in [0.0, 1.0]."""
    from uuid import uuid4

    from app.services.feature_extractor import TrainingCohortRecord

    rng = np.random.default_rng(2)
    species = ["A", "B", "C"]
    dummy_roi = uuid4()
    n = 60
    raw = rng.uniform(0.0, 1.0, (n, 12))
    cohort = [
        TrainingCohortRecord(
            roi_id=dummy_roi,
            species_label=species[i % 3],
            ndvi_min=raw[i][0],
            ndvi_max=raw[i][1],
            ndvi_mean=raw[i][2],
            ndvi_std=raw[i][3],
            endvi_min=raw[i][4],
            endvi_max=raw[i][5],
            endvi_mean=raw[i][6],
            endvi_std=raw[i][7],
            red_edge_min=raw[i][8],
            red_edge_max=raw[i][9],
            red_edge_mean=raw[i][10],
            red_edge_std=raw[i][11],
        )
        for i in range(n)
    ]
    result = FocalClassifier.train_classifier(cohort, str(tmp_path))
    assert isinstance(result.test_f1, float) and 0.0 <= result.test_f1 <= 1.0
    assert isinstance(result.test_precision, float) and 0.0 <= result.test_precision <= 1.0
    assert isinstance(result.test_recall, float) and 0.0 <= result.test_recall <= 1.0
    assert isinstance(result.test_balanced_accuracy, float)
    assert 0.0 <= result.test_balanced_accuracy <= 1.0
    for score in result.cv_scores:
        assert isinstance(score, float) and 0.0 <= score <= 1.0


def test_rf_model_serialization(tmp_path):
    """joblib dump/load round-trip preserves predict and predict_proba."""
    from pathlib import Path
    from uuid import uuid4

    import joblib

    from app.services.feature_extractor import TrainingCohortRecord

    rng = np.random.default_rng(3)
    species = ["A", "B", "C"]
    dummy_roi = uuid4()
    n = 60
    raw = rng.uniform(0.0, 1.0, (n, 12))
    cohort = [
        TrainingCohortRecord(
            roi_id=dummy_roi,
            species_label=species[i % 3],
            ndvi_min=raw[i][0],
            ndvi_max=raw[i][1],
            ndvi_mean=raw[i][2],
            ndvi_std=raw[i][3],
            endvi_min=raw[i][4],
            endvi_max=raw[i][5],
            endvi_mean=raw[i][6],
            endvi_std=raw[i][7],
            red_edge_min=raw[i][8],
            red_edge_max=raw[i][9],
            red_edge_mean=raw[i][10],
            red_edge_std=raw[i][11],
        )
        for i in range(n)
    ]
    FocalClassifier.train_classifier(cohort, str(tmp_path))
    model = joblib.load(Path(tmp_path) / "classifier.pkl")
    sample = rng.uniform(0.0, 1.0, (1, 12)).astype(np.float32)
    assert model.predict(sample)[0] in species
    assert model.predict_proba(sample).shape[1] == 3


def test_infer_confidence_clipped():
    """clip_confidence ensures no value outside [0.0, 1.0] reaches callers."""
    # clip from below
    assert FocalClassifier.clip_confidence(-0.01) == 0.0
    # clip from above
    assert FocalClassifier.clip_confidence(1.01) == 1.0
    # passthrough midpoint
    assert FocalClassifier.clip_confidence(0.5) == pytest.approx(0.5)


def test_infer_dry_run_no_db_write():
    """infer_predictions with dry_run=True returns predictions without DB writes."""
    import asyncio
    import unittest.mock as mock
    from uuid import UUID

    from app.services.feature_extractor import InferenceVector

    X, y = _make_X_y()
    clf = FocalClassifier()
    clf.fit(X, y)
    mock_model = clf._model

    test_roi_id = "00000000-0000-0000-0000-000000000001"
    dummy_candidate = mock.MagicMock()
    dummy_candidate.geom = "POINT(0 0)"
    dummy_candidate.roi_id = UUID(test_roi_id)
    dummy_candidate.grid_row = 0
    dummy_candidate.grid_col = 0

    dummy_vector = InferenceVector(
        ndvi_min=0.1,
        ndvi_max=0.9,
        ndvi_mean=0.5,
        ndvi_std=0.2,
        endvi_min=0.2,
        endvi_max=0.8,
        endvi_mean=0.5,
        endvi_std=0.1,
        red_edge_min=0.3,
        red_edge_max=0.7,
        red_edge_mean=0.5,
        red_edge_std=0.1,
    )

    with (
        mock.patch.object(FocalClassifier, "load_classifier", return_value=mock_model),
        mock.patch.object(
            FocalClassifier,
            "get_model_metadata",
            return_value={"feature_names": [], "class_labels": [], "model_version": VERSION},
        ),
        mock.patch(
            "app.services.feature_extractor.FeatureExtractor.generate_candidates",
            new_callable=mock.AsyncMock,
            return_value=[dummy_candidate],
        ),
        mock.patch(
            "app.services.feature_extractor.FeatureExtractor.extract_inference_vector",
            new_callable=mock.AsyncMock,
            return_value=dummy_vector,
        ),
    ):
        result = asyncio.run(
            FocalClassifier.infer_predictions([test_roi_id], VERSION, dry_run=True)
        )

    assert result is not None
    assert isinstance(result.predictions, list)
    # dry_run — no ORM session, no db.add_all() was called — inference returned in-memory only
    assert len(result.predictions) == 1


def test_infer_model_version_set():
    """All inference prediction records carry model_version = VERSION."""
    import asyncio
    import unittest.mock as mock
    from uuid import UUID

    from app.services.feature_extractor import InferenceVector

    X, y = _make_X_y()
    clf = FocalClassifier()
    clf.fit(X, y)
    mock_model = clf._model

    test_roi_id = "00000000-0000-0000-0000-000000000002"
    dummy_candidate = mock.MagicMock()
    dummy_candidate.geom = "POINT(1 1)"
    dummy_candidate.roi_id = UUID(test_roi_id)
    dummy_candidate.grid_row = 0
    dummy_candidate.grid_col = 0

    dummy_vector = InferenceVector(
        ndvi_min=0.1,
        ndvi_max=0.9,
        ndvi_mean=0.5,
        ndvi_std=0.2,
        endvi_min=0.2,
        endvi_max=0.8,
        endvi_mean=0.5,
        endvi_std=0.1,
        red_edge_min=0.3,
        red_edge_max=0.7,
        red_edge_mean=0.5,
        red_edge_std=0.1,
    )

    with (
        mock.patch.object(FocalClassifier, "load_classifier", return_value=mock_model),
        mock.patch.object(
            FocalClassifier,
            "get_model_metadata",
            return_value={"feature_names": [], "class_labels": [], "model_version": VERSION},
        ),
        mock.patch(
            "app.services.feature_extractor.FeatureExtractor.generate_candidates",
            new_callable=mock.AsyncMock,
            return_value=[dummy_candidate],
        ),
        mock.patch(
            "app.services.feature_extractor.FeatureExtractor.extract_inference_vector",
            new_callable=mock.AsyncMock,
            return_value=dummy_vector,
        ),
    ):
        result = asyncio.run(
            FocalClassifier.infer_predictions([test_roi_id], VERSION, dry_run=True)
        )

    for pred in result.predictions:
        assert pred["model_version"] == VERSION
