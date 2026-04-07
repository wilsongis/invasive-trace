"""Benchmark cohort assembly and train/test split alignment.

This module builds a matched benchmark dataset from existing ROI,
observation, and spectral inputs so that the Stage 2 baseline and
AlphaEarth benchmark variant can be evaluated on identical conditions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

DEFAULT_RANDOM_STATE = 42
DEFAULT_TEST_SIZE = 0.2


@dataclass
class BenchmarkCohort:
    """A matched cohort for baseline vs benchmark comparison."""

    roi_id: str
    year: int
    label_set: list[str]
    X_baseline: np.ndarray | None = None  # [ndvi, endvi, red_edge, elevation]
    y_labels: list[str] | None = None
    X_train: np.ndarray | None = None
    X_test: np.ndarray | None = None
    y_train: list[str] | None = None
    y_test: list[str] | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_split(self) -> bool:
        """Return True if train/test splits have been computed."""
        return self.X_train is not None and self.y_train is not None


class BenchmarkDatasetBuilder:
    """Assembles benchmark cohorts aligned to the Stage 2 baseline."""

    def __init__(
        self,
        random_state: int = DEFAULT_RANDOM_STATE,
        test_size: float = DEFAULT_TEST_SIZE,
    ) -> None:
        self._random_state = random_state
        self._test_size = test_size

    def build_cohort(
        self,
        roi_id: str,
        year: int,
        feature_matrix: np.ndarray,
        labels: list[str],
    ) -> BenchmarkCohort:
        """Build a benchmark cohort from feature matrix and labels.

        Args:
            roi_id: ROI identifier string.
            year: Target year for the cohort.
            feature_matrix: Feature array of shape (n_samples, n_features).
            labels: Species label strings matching feature_matrix rows.

        Returns:
            BenchmarkCohort with aligned data.

        Raises:
            ValueError: If feature_matrix and labels have mismatched lengths.
        """
        if len(feature_matrix) != len(labels):
            raise ValueError(
                f"feature_matrix rows ({len(feature_matrix)}) != labels count ({len(labels)})"
            )

        if len(feature_matrix) == 0:
            raise ValueError("Cannot build cohort from empty feature matrix")

        label_set = sorted(set(labels))
        logger.info(
            "benchmark_cohort_built roi=%s year=%s n_samples=%d labels=%s",
            roi_id,
            year,
            len(feature_matrix),
            label_set,
        )

        return BenchmarkCohort(
            roi_id=roi_id,
            year=year,
            label_set=label_set,
            X_baseline=feature_matrix,
            y_labels=labels,
        )

    def compute_splits(self, cohort: BenchmarkCohort) -> BenchmarkCohort:
        """Compute reproducible train/test splits for a cohort.

        Args:
            cohort: A BenchmarkCohort with X_baseline and y_labels set.

        Returns:
            The same cohort with X_train, X_test, y_train, y_test populated.

        Raises:
            ValueError: If the cohort lacks baseline data or labels.
        """
        if cohort.X_baseline is None or cohort.y_labels is None:
            raise ValueError("Cohort must have X_baseline and y_labels set")

        X_train, X_test, y_train, y_test = train_test_split(
            cohort.X_baseline,
            cohort.y_labels,
            test_size=self._test_size,
            random_state=self._random_state,
            stratify=cohort.y_labels if len(set(cohort.y_labels)) > 1 else None,
        )

        cohort.X_train = X_train
        cohort.X_test = X_test
        cohort.y_train = list(y_train)
        cohort.y_test = list(y_test)

        logger.info(
            "benchmark_splits roi=%s train=%d test=%d",
            cohort.roi_id,
            len(X_train),
            len(X_test),
        )

        return cohort

    def load_from_csv(
        self,
        roi_id: str,
        year: int,
        csv_path: Path,
        label_column: str = "species_label",
    ) -> BenchmarkCohort:
        """Load a cohort from a CSV file.

        Args:
            roi_id: ROI identifier string.
            year: Target year for the cohort.
            csv_path: Path to the CSV file.
            label_column: Name of the species label column.

        Returns:
            BenchmarkCohort with data loaded from CSV.
        """
        import csv

        if not csv_path.exists():
            raise FileNotFoundError(f"Benchmark CSV not found: {csv_path}")

        features: list[list[float]] = []
        labels: list[str] = []

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                labels.append(row[label_column])
                feature_row = [
                    float(row.get("ndvi", 0)),
                    float(row.get("endvi", 0)),
                    float(row.get("red_edge", 0)),
                    float(row.get("elevation", 0)),
                ]
                features.append(feature_row)

        feature_matrix = np.array(features, dtype=np.float64)
        cohort = self.build_cohort(roi_id, year, feature_matrix, labels)
        return self.compute_splits(cohort)
