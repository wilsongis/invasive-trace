"""Unit tests for AlphaEarth benchmark orchestration."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.alphaearth_benchmark import (
    BenchmarkMetrics,
    run_baseline_comparison,
    run_benchmark_comparison,
    run_full_comparison,
)
from app.services.benchmark_dataset import BenchmarkDatasetBuilder


class TestAlphaEarthBenchmarkOrchestration:
    """Tests for baseline vs benchmark comparison orchestration."""

    def _make_cohort(self, n_samples: int = 100):
        """Helper to create a test cohort with splits."""
        rng = np.random.default_rng(42)
        X = rng.random((n_samples, 4))
        labels = ["species_a"] * (n_samples // 2) + ["species_b"] * (n_samples - n_samples // 2)
        builder = BenchmarkDatasetBuilder()
        cohort = builder.build_cohort("roi-1", 2024, X, labels)
        return builder.compute_splits(cohort)

    def test_run_baseline_comparison(self) -> None:
        """Baseline comparison should return valid metrics."""
        cohort = self._make_cohort()
        metrics = run_baseline_comparison(cohort)

        assert isinstance(metrics, BenchmarkMetrics)
        assert metrics.model_version == "rf-v0.1.0"
        assert 0.0 <= metrics.precision <= 1.0
        assert 0.0 <= metrics.recall <= 1.0
        assert 0.0 <= metrics.f1 <= 1.0
        assert metrics.runtime_seconds >= 0
        assert metrics.n_train > 0
        assert metrics.n_test > 0

    def test_run_baseline_comparison_unsplit(self) -> None:
        """Should raise ValueError when cohort has no splits."""
        builder = BenchmarkDatasetBuilder()
        X = np.random.default_rng(42).random((10, 4))
        labels = ["species_a"] * 5 + ["species_b"] * 5
        cohort = builder.build_cohort("roi-1", 2024, X, labels)

        with pytest.raises(ValueError, match="train/test splits"):
            run_baseline_comparison(cohort)

    def test_run_benchmark_comparison(self) -> None:
        """Benchmark comparison should return valid metrics."""
        cohort = self._make_cohort()
        rng = np.random.default_rng(42)
        X_ae_train = rng.random((80, 64))
        X_ae_test = rng.random((20, 64))

        metrics = run_benchmark_comparison(cohort, X_ae_train, X_ae_test)

        assert isinstance(metrics, BenchmarkMetrics)
        assert metrics.model_version == "alphaearth-benchmark-v0.1.0"
        assert 0.0 <= metrics.f1 <= 1.0

    def test_run_benchmark_comparison_wrong_dim(self) -> None:
        """Should raise ValueError for wrong embedding dimension."""
        cohort = self._make_cohort()
        rng = np.random.default_rng(42)
        X_ae_train = rng.random((80, 32))  # Wrong: should be 64
        X_ae_test = rng.random((20, 32))

        with pytest.raises(ValueError, match="Expected 64-dim"):
            run_benchmark_comparison(cohort, X_ae_train, X_ae_test)

    def test_run_full_comparison_both(self) -> None:
        """Full comparison should run both baseline and benchmark."""
        cohort = self._make_cohort()
        rng = np.random.default_rng(42)
        X_ae_train = rng.random((80, 64))
        X_ae_test = rng.random((20, 64))

        comparison = run_full_comparison(cohort, X_ae_train, X_ae_test)

        assert comparison.baseline is not None
        assert comparison.benchmark is not None
        assert comparison.cohort_roi_id == "roi-1"
        assert comparison.cohort_year == 2024

    def test_run_full_comparison_no_alphaearth(self) -> None:
        """Full comparison should skip benchmark when no AE features."""
        cohort = self._make_cohort()
        comparison = run_full_comparison(cohort)

        assert comparison.baseline is not None
        assert comparison.benchmark is None
        assert "no_alphaearth_features" in comparison.metadata.get("benchmark_skip_reason", "")
