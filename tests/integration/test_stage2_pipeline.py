"""Integration tests for Stage 2 pipeline."""

from uuid import uuid4

import numpy as np

from app.ml.stage2_classifier import FocalClassifier
from app.services.feature_extractor import FeatureExtractor, TrainingCohortRecord


def test_stage2_imports():
    """Core Stage 2 modules import without error."""
    assert FocalClassifier is not None
    assert FeatureExtractor is not None


def test_model_artifact_dir_exists(tmp_path):
    """Training artifact output dir is created if it doesn't exist."""
    from pathlib import Path

    rng = np.random.default_rng(0)
    species = ["Bromus tectorum", "Tamarix ramosissima", "Centaurea solstitialis"]
    dummy_roi = uuid4()
    raw = rng.uniform(0.0, 1.0, (60, 12)).astype(float)
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
        for i in range(60)
    ]
    output_dir = str(tmp_path / "FocalClassifier" / "rf-v0.1.0")
    result = FocalClassifier.train_classifier(cohort, output_dir)

    assert (Path(output_dir) / "classifier.pkl").exists()
    assert (Path(output_dir) / "metadata.json").exists()
    assert (Path(output_dir) / "feature_names.txt").exists()
    assert (Path(output_dir) / "class_labels.txt").exists()
    assert result.test_f1 is not None
    assert result.model_version == "rf-v0.1.0"


def test_rf_training_metrics_in_valid_range(tmp_path):
    """RandomForest training produces metrics in [0, 1]."""
    rng = np.random.default_rng(99)
    species = ["Species A", "Species B", "Species C"]
    dummy_roi = uuid4()
    raw = rng.uniform(0.0, 1.0, (90, 12)).astype(float)
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
        for i in range(90)
    ]
    result = FocalClassifier.train_classifier(cohort, str(tmp_path))
    assert 0.0 <= result.test_f1 <= 1.0
    assert 0.0 <= result.test_precision <= 1.0
    assert 0.0 <= result.test_recall <= 1.0
    assert 0.0 <= result.test_balanced_accuracy <= 1.0
    assert len(result.cv_scores) == 5


def test_rf_serialise_deserialise(tmp_path):
    """A trained classifier can round-trip through joblib and still predict."""
    from pathlib import Path

    import joblib

    rng = np.random.default_rng(7)
    dummy_roi = uuid4()
    raw = rng.uniform(0.0, 1.0, (60, 12)).astype(float)
    species = ["A", "B", "C"]
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
        for i in range(60)
    ]
    out_dir = str(tmp_path)
    FocalClassifier.train_classifier(cohort, out_dir)

    # Reload and predict — load directly via joblib since load_classifier uses the
    # canonical registry path; here we just verify the artifact round-trips.
    loaded_model = joblib.load(Path(out_dir) / "classifier.pkl")
    sample = rng.uniform(0.0, 1.0, (1, 12)).astype(np.float32)
    pred_label = loaded_model.predict(sample)[0]
    assert pred_label in species


def test_stage2_pipeline_end_to_end(tmp_path):
    """SC-001: ≥99% of eligible candidates receive a written prediction."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import uuid4

    import joblib
    import numpy as np

    from app.ml.stage2_classifier import FocalClassifier
    from app.services.feature_extractor import InferenceVector

    # ------------------------------------------------------------------
    # Build a real trained artifact so load_classifier succeeds
    # ------------------------------------------------------------------
    rng = np.random.default_rng(42)
    species = ["Bromus tectorum", "Tamarix ramosissima", "Centaurea solstitialis"]
    dummy_roi = uuid4()
    raw = rng.uniform(0.0, 1.0, (60, 12)).astype(float)
    from app.services.feature_extractor import TrainingCohortRecord  # noqa: PLC0415

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
        for i in range(60)
    ]
    out_dir = str(tmp_path / "FocalClassifier" / "rf-v0.1.0")
    FocalClassifier.train_classifier(cohort, out_dir)

    # ------------------------------------------------------------------
    # Mock FeatureExtractor to return N fully-eligible candidates
    # ------------------------------------------------------------------
    N_CANDIDATES = 20
    roi_id = str(uuid4())

    def _make_inference_vector() -> InferenceVector:
        r = rng.uniform(0.0, 1.0, 12).tolist()
        return InferenceVector(
            ndvi_min=r[0],
            ndvi_max=r[1],
            ndvi_mean=r[2],
            ndvi_std=r[3],
            endvi_min=r[4],
            endvi_max=r[5],
            endvi_mean=r[6],
            endvi_std=r[7],
            red_edge_min=r[8],
            red_edge_max=r[9],
            red_edge_mean=r[10],
            red_edge_std=r[11],
        )

    fake_candidates = [MagicMock(geom=MagicMock()) for _ in range(N_CANDIDATES)]

    with (
        patch(
            "app.ml.stage2_classifier.FocalClassifier.load_classifier",
            return_value=joblib.load(f"{out_dir}/classifier.pkl"),
        ),
        patch(
            "app.ml.stage2_classifier.FocalClassifier.get_model_metadata",
            return_value={"model_version": "rf-v0.1.0"},
        ),
        patch(
            "app.services.feature_extractor.FeatureExtractor.generate_candidates",
            new=AsyncMock(return_value=fake_candidates),
        ),
        patch(
            "app.services.feature_extractor.FeatureExtractor.extract_inference_vector",
            new=AsyncMock(side_effect=lambda roi, geom: _make_inference_vector()),
        ),
    ):
        result = asyncio.run(
            FocalClassifier.infer_predictions(
                roi_ids=[roi_id],
                model_version="rf-v0.1.0",
                dry_run=True,
            )
        )

    candidates_generated = N_CANDIDATES
    predictions_written = len(result.predictions)

    # SC-001: ≥99% of eligible candidates must be classified
    assert predictions_written / candidates_generated >= 0.99, (
        f"Expected ≥99% coverage: {predictions_written}/{candidates_generated}"
    )
