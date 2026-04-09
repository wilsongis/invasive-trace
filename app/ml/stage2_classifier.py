"""Stage 2 — FocalClassifier (rf-v0.1.0).

RandomForest species-level classification on [ndvi, endvi, red_edge, elevation].
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import cross_val_score, train_test_split

logger = logging.getLogger(__name__)

VERSION = "rf-v0.1.0"
ARTIFACT_PATH = Path("models/FocalClassifier/rf-v0.1.0/classifier.pkl")
METADATA_PATH = Path("models/FocalClassifier/rf-v0.1.0/metadata.json")
FEATURE_NAMES_PATH = Path("models/FocalClassifier/rf-v0.1.0/feature_names.txt")
CLASS_LABELS_PATH = Path("models/FocalClassifier/rf-v0.1.0/class_labels.txt")
README_PATH = Path("models/FocalClassifier/rf-v0.1.0/README.md")

# Feature names for the 12-element vector
FEATURE_NAMES = [
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


class FocalClassifierArtifactMissingError(FileNotFoundError):
    """Raised when the Stage 2 artifact is absent at the registered path."""


class TrainingResult:
    """Result of training a classifier."""

    def __init__(
        self,
        model_version: str,
        sample_count: int,
        cv_scores: list[float],
        test_f1: float,
        test_precision: float,
        test_recall: float,
        test_balanced_accuracy: float,
        class_labels: list[str],
    ):
        self.model_version = model_version
        self.sample_count = sample_count
        self.cv_scores = cv_scores
        self.test_f1 = test_f1
        self.test_precision = test_precision
        self.test_recall = test_recall
        self.test_balanced_accuracy = test_balanced_accuracy
        self.class_labels = class_labels


class InferenceResult:
    """Result of running inference."""

    def __init__(self, predictions: list[dict[str, Any]], total_time_sec: float):
        self.predictions = predictions
        self.total_time_sec = total_time_sec


class FocalClassifier:
    """RandomForest invasive species classifier.

    Feature vector: [ndvi_min, ndvi_max, ndvi_mean, ndvi_std,
                     endvi_min, endvi_max, endvi_mean, endvi_std,
                     red_edge_min, red_edge_max, red_edge_mean, red_edge_std]

    Training API : fit(X, y)
    Inference API: predict(X)
    Load API     : load()
    """

    VERSION = VERSION
    ARTIFACT_PATH = ARTIFACT_PATH
    METADATA_PATH = METADATA_PATH
    FEATURE_NAMES_PATH = FEATURE_NAMES_PATH
    CLASS_LABELS_PATH = CLASS_LABELS_PATH
    README_PATH = README_PATH

    def __init__(self) -> None:
        self._model: RandomForestClassifier | None = None
        self._feature_names = FEATURE_NAMES
        self._class_labels: list[str] | None = None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, X: np.ndarray, y: list[str]) -> FocalClassifier:
        """Train on feature matrix X with species label targets y.

        Args:
            X: Feature matrix of shape (n_samples, 12) — 12 spectral features.
            y: Species label strings (e.g. "Bromus tectorum") sourced from
               ground_truth_observations.species_label (FR-012).

        Returns:
            self (for method chaining).
        """
        if len(X) == 0:
            raise ValueError("Cannot fit FocalClassifier on empty training set")

        self._model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
        )
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
            X: Feature array of shape (1, 12) or (12,) — 12 spectral features.

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

    # ------------------------------------------------------------------
    # Training Methods
    # ------------------------------------------------------------------

    @staticmethod
    def train_classifier(
        training_cohort: list, output_dir: str, force_retrain: bool = False
    ) -> TrainingResult:
        """Train a RandomForest classifier on the training cohort.

        Args:
            training_cohort: List of TrainingCohortRecord objects
            output_dir: Directory to save model artifacts
            force_retrain: Whether to retrain even if model exists

        Returns:
            TrainingResult with model metrics
        """
        # Convert training cohort to feature matrix and labels
        features = []
        labels = []

        for record in training_cohort:
            # Assemble the 12-element aggregate feature vector
            feature_vector = [
                record.ndvi_min,
                record.ndvi_max,
                record.ndvi_mean,
                record.ndvi_std,
                record.endvi_min,
                record.endvi_max,
                record.endvi_mean,
                record.endvi_std,
                record.red_edge_min,
                record.red_edge_max,
                record.red_edge_mean,
                record.red_edge_std,
            ]
            features.append(feature_vector)
            labels.append(record.species_label)

        X = np.array(features, dtype=np.float32)
        y = labels

        # Check if we have enough data
        if len(X) < 10:
            raise ValueError(f"Insufficient training data: {len(X)} samples. Need at least 10.")

        # Split into train/test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )

        # Perform cross-validation
        cv_scores = cross_val_score(
            RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=42,
            ),
            X_train,
            y_train,
            cv=5,
            scoring="f1_macro",
        )

        # Train final model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
        )
        model.fit(X_train, y_train)

        # Evaluate on test set
        y_pred = model.predict(X_test)
        test_f1 = float(f1_score(y_test, y_pred, average="macro"))
        test_precision = float(precision_score(y_test, y_pred, average="macro"))
        test_recall = float(recall_score(y_test, y_pred, average="macro"))
        test_balanced_accuracy = float(balanced_accuracy_score(y_test, y_pred))

        # Check if model meets minimum threshold
        if test_f1 < 0.50:
            logger.warning("Stage 2 classifier F1-macro (%.4f) below threshold of 0.50", test_f1)

        # Save model artifacts
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = output_path / "classifier.pkl"
        joblib.dump(model, model_path)

        # Save metadata
        metadata = {
            "model_version": VERSION,
            "training_date": time.strftime("%Y-%m-%d"),  # Dynamic training date
            "training_sample_count": len(X),
            "training_sample_count_by_species": {},
            "feature_names": FEATURE_NAMES,
            "class_labels": list(set(y)),
            "hyperparameters": {
                "n_estimators": 100,
                "max_depth": 15,
                "min_samples_leaf": 5,
                "class_weight": "balanced",
            },
            "cv_f1_macro_mean": float(np.mean(cv_scores)),
            "cv_f1_macro_std": float(np.std(cv_scores)),
            "cv_fold_scores": cv_scores.tolist(),
            "test_f1_macro": float(test_f1),
            "test_precision_macro": float(test_precision),
            "test_recall_macro": float(test_recall),
            "test_balanced_accuracy": float(test_balanced_accuracy),
        }

        # Add sample count by species
        species_counts = {}
        for label in y:
            species_counts[label] = species_counts.get(label, 0) + 1
        metadata["training_sample_count_by_species"] = species_counts

        metadata_path = output_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Save feature names
        feature_names_path = output_path / "feature_names.txt"
        with open(feature_names_path, "w") as f:
            f.write("\n".join(FEATURE_NAMES))

        # Save class labels
        class_labels_path = output_path / "class_labels.txt"
        with open(class_labels_path, "w") as f:
            f.write("\n".join(list(set(y))))

        # Save README
        readme_content = f"""# Model Card: FocalClassifier {VERSION}

## Training Information
- Training date: {time.strftime("%Y-%m-%d")}
- Training samples: {len(X)}
- Features: {", ".join(FEATURE_NAMES)}
- Classes: {", ".join(list(set(y)))}

## Model Performance
- Cross-validation F1-macro: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}
- Test F1-macro: {test_f1:.4f}
- Test Precision-macro: {test_precision:.4f}
- Test Recall-macro: {test_recall:.4f}
- Test Balanced Accuracy: {test_balanced_accuracy:.4f}
"""
        readme_path = output_path / "README.md"
        with open(readme_path, "w") as f:
            f.write(readme_content)

        logger.info(
            "stage2_trained version=%s samples=%d cv_f1=%.4f test_f1=%.4f",
            VERSION,
            len(X),
            np.mean(cv_scores),
            test_f1,
        )

        return TrainingResult(
            model_version=VERSION,
            sample_count=len(X),
            cv_scores=cv_scores.tolist(),
            test_f1=test_f1,
            test_precision=test_precision,
            test_recall=test_recall,
            test_balanced_accuracy=test_balanced_accuracy,
            class_labels=list(set(y)),
        )

    @staticmethod
    def load_classifier(version: str) -> RandomForestClassifier:
        """Load a trained classifier by version.

        Args:
            version: Model version string

        Returns:
            Loaded RandomForestClassifier
        """
        model_path = Path(f"models/FocalClassifier/{version}/classifier.pkl")
        if not model_path.exists():
            raise FocalClassifierArtifactMissingError(
                f"Stage 2 classifier artifact missing: {model_path}"
            )
        return joblib.load(model_path)

    @staticmethod
    def get_model_metadata(version: str) -> dict[str, Any]:
        """Load model metadata.

        Args:
            version: Model version string

        Returns:
            Dictionary with model metadata
        """
        metadata_path = Path(f"models/FocalClassifier/{version}/metadata.json")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Model metadata missing: {metadata_path}")

        with open(metadata_path) as f:
            return json.load(f)

    @staticmethod
    def clip_confidence(confidence: float) -> float:
        """Ensure confidence is bounded between 0.0 and 1.0.

        Args:
            confidence: Raw confidence value

        Returns:
            Clamped confidence value
        """
        return max(0.0, min(1.0, confidence))

    # ------------------------------------------------------------------
    # Inference Methods
    # ------------------------------------------------------------------

    @staticmethod
    async def infer_predictions(
        roi_ids: list[str], model_version: str, dry_run: bool = False
    ) -> InferenceResult:
        """Run inference on candidate locations for given ROIs.

        Args:
            roi_ids: List of ROI IDs to run inference on
            model_version: Version of the model to use
            dry_run: If True, don't persist results to DB

        Returns:
            InferenceResult with predictions
        """
        import time
        from uuid import UUID

        from app.services.feature_extractor import FeatureExtractor

        start_time = time.time()

        # Load classifier
        try:
            classifier = FocalClassifier.load_classifier(model_version)
            logger.info("Loaded classifier version %s", model_version)
        except Exception as e:
            logger.error("Failed to load classifier: %s", e)
            raise

        # Get model metadata
        try:
            FocalClassifier.get_model_metadata(model_version)
            logger.info("Model metadata loaded for version %s", model_version)
        except Exception as e:
            logger.error("Failed to load model metadata: %s", e)
            raise

        predictions = []

        # Run inference for each ROI
        for roi_id in roi_ids:
            logger.info("Processing ROI %s", roi_id)

            # Convert string to UUID if needed
            roi_uuid = UUID(roi_id) if isinstance(roi_id, str) else roi_id

            # Generate candidate locations
            candidates = await FeatureExtractor.generate_candidates(roi_uuid)
            logger.info("Generated %d candidate locations for ROI %s", len(candidates), roi_id)

            # Process each candidate
            for candidate in candidates:
                # Extract inference vector
                inference_vector = await FeatureExtractor.extract_inference_vector(
                    roi_uuid, candidate.geom
                )
                if inference_vector is None:
                    logger.warning(
                        "Skipping candidate at %s due to missing features", candidate.geom
                    )
                    continue

                # Convert to feature array
                feature_array = [
                    inference_vector.ndvi_min,
                    inference_vector.ndvi_max,
                    inference_vector.ndvi_mean,
                    inference_vector.ndvi_std,
                    inference_vector.endvi_min,
                    inference_vector.endvi_max,
                    inference_vector.endvi_mean,
                    inference_vector.endvi_std,
                    inference_vector.red_edge_min,
                    inference_vector.red_edge_max,
                    inference_vector.red_edge_mean,
                    inference_vector.red_edge_std,
                ]

                # Predict — load_classifier returns a raw RandomForestClassifier;
                # call .predict() and .predict_proba() separately.
                try:
                    X_arr = np.atleast_2d(feature_array)
                    species_label: str = classifier.predict(X_arr)[0]
                    proba = classifier.predict_proba(X_arr)[0]
                    confidence = FocalClassifier.clip_confidence(float(np.max(proba)))
                    logger.info(
                        "ROI %s candidate %s: %s (confidence: %.4f)",
                        roi_id,
                        candidate.geom,
                        species_label,
                        confidence,
                    )

                    # Create prediction record
                    prediction = {
                        "roi_id": str(roi_id),
                        "species_label": species_label,
                        "confidence": confidence,
                        "geom": candidate.geom,
                        "model_version": model_version,
                        "predicted_at": time.time(),
                    }
                    predictions.append(prediction)
                except Exception as e:
                    logger.error(
                        "Prediction failed for ROI %s candidate %s: %s", roi_id, candidate.geom, e
                    )
                    continue

        total_time = time.time() - start_time
        logger.info(
            "Stage 2 inference completed for %d ROIs in %.2f seconds", len(roi_ids), total_time
        )

        return InferenceResult(predictions=predictions, total_time_sec=total_time)
