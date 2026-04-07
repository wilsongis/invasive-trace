"""Unit tests for benchmark dataset assembly."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.benchmark_dataset import BenchmarkCohort, BenchmarkDatasetBuilder


class TestBenchmarkDatasetBuilder:
    """Tests for BenchmarkDatasetBuilder cohort assembly and splits."""

    def test_build_cohort_basic(self) -> None:
        """Cohort should be built from feature matrix and labels."""
        builder = BenchmarkDatasetBuilder()
        X = np.array([[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]])
        labels = ["species_a", "species_b"]

        cohort = builder.build_cohort("roi-1", 2024, X, labels)

        assert cohort.roi_id == "roi-1"
        assert cohort.year == 2024
        assert cohort.label_set == ["species_a", "species_b"]
        assert cohort.X_baseline is not None
        assert len(cohort.X_baseline) == 2
        assert not cohort.is_split

    def test_build_cohort_mismatched_lengths(self) -> None:
        """Should raise ValueError when feature rows != label count."""
        builder = BenchmarkDatasetBuilder()
        X = np.array([[0.1, 0.2, 0.3, 0.4]])
        labels = ["species_a", "species_b"]

        with pytest.raises(ValueError, match="feature_matrix rows"):
            builder.build_cohort("roi-1", 2024, X, labels)

    def test_build_cohort_empty(self) -> None:
        """Should raise ValueError for empty feature matrix."""
        builder = BenchmarkDatasetBuilder()
        X = np.array([]).reshape(0, 4)
        labels: list[str] = []

        with pytest.raises(ValueError, match="empty feature matrix"):
            builder.build_cohort("roi-1", 2024, X, labels)

    def test_compute_splits(self) -> None:
        """Should compute train/test splits with correct sizes."""
        builder = BenchmarkDatasetBuilder(test_size=0.2)
        X = np.random.default_rng(42).random((100, 4))
        labels = ["species_a"] * 50 + ["species_b"] * 50

        cohort = builder.build_cohort("roi-1", 2024, X, labels)
        cohort = builder.compute_splits(cohort)

        assert cohort.is_split
        assert cohort.X_train is not None
        assert cohort.X_test is not None
        assert cohort.y_train is not None
        assert cohort.y_test is not None
        assert len(cohort.y_train) == 80  # 80% of 100
        assert len(cohort.y_test) == 20  # 20% of 100

    def test_compute_splits_unlabeled(self) -> None:
        """Should raise ValueError when y_labels is None."""
        builder = BenchmarkDatasetBuilder()
        cohort = BenchmarkCohort(
            roi_id="roi-1",
            year=2024,
            label_set=["species_a"],
            X_baseline=np.random.default_rng(42).random((10, 4)),
            y_labels=None,
        )

        with pytest.raises(ValueError, match="X_baseline and y_labels"):
            builder.compute_splits(cohort)

    def test_compute_splits_single_class(self) -> None:
        """Should handle single-class labels without stratification error."""
        builder = BenchmarkDatasetBuilder()
        X = np.random.default_rng(42).random((10, 4))
        labels = ["species_a"] * 10

        cohort = builder.build_cohort("roi-1", 2024, X, labels)
        cohort = builder.compute_splits(cohort)

        assert cohort.is_split
        assert cohort.y_train is not None
        assert cohort.y_test is not None
        assert len(cohort.y_train) > 0
        assert len(cohort.y_test) > 0
