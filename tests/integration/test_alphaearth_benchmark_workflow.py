"""Integration test for Wave 1.5 AlphaEarth benchmark workflow.

This test validates the end-to-end benchmark execution path using
mocked/synthetic data to avoid requiring actual Earth Engine access.
"""

from __future__ import annotations

import numpy as np

from app.services.alphaearth_benchmark import (
    run_full_comparison,
)
from app.services.alphaearth_client import AlphaEarthClient
from app.services.benchmark_dataset import BenchmarkDatasetBuilder
from app.services.benchmark_report import (
    RECOMMENDATION_DEFER,
    RECOMMENDATION_GO,
    RECOMMENDATION_NO_GO,
    generate_recommendation,
)


class TestAlphaEarthBenchmarkWorkflow:
    """End-to-end benchmark workflow tests."""

    def test_full_workflow_with_synthetic_data(self) -> None:
        """Complete benchmark workflow should produce a valid recommendation."""
        # Step 1: Check availability (will skip without EE access)
        client = AlphaEarthClient()
        availability = client.check_coverage("POINT(-100 40)", 2024)
        assert availability.available is False  # Expected: no EE access

        # Step 2: Assemble synthetic cohort
        rng = np.random.default_rng(42)
        n_samples = 100
        X_baseline = rng.random((n_samples, 4))
        labels = ["Bromus tectorum"] * 50 + ["Native species"] * 50

        builder = BenchmarkDatasetBuilder()
        cohort = builder.build_cohort("roi-test", 2024, X_baseline, labels)
        cohort = builder.compute_splits(cohort)

        assert cohort.is_split
        assert cohort.y_train is not None
        assert cohort.y_test is not None

        # Step 3: Generate synthetic AlphaEarth features
        X_ae_train = rng.random((len(cohort.y_train), 64))
        X_ae_test = rng.random((len(cohort.y_test), 64))

        # Step 4: Run full comparison
        comparison = run_full_comparison(cohort, X_ae_train, X_ae_test)

        assert comparison.baseline is not None
        assert comparison.benchmark is not None
        assert comparison.cohort_roi_id == "roi-test"
        assert comparison.cohort_year == 2024

        # Step 5: Generate recommendation
        report = generate_recommendation(comparison)
        assert report.recommendation in (
            RECOMMENDATION_GO,
            RECOMMENDATION_NO_GO,
            RECOMMENDATION_DEFER,
        )
        assert report.rationale
        assert report.generated_at

    def test_workflow_skip_benchmark_no_features(self) -> None:
        """Workflow should handle missing AlphaEarth features gracefully."""
        rng = np.random.default_rng(42)
        X = rng.random((50, 4))
        labels = ["species_a"] * 25 + ["species_b"] * 25

        builder = BenchmarkDatasetBuilder()
        cohort = builder.build_cohort("roi-skip", 2024, X, labels)
        cohort = builder.compute_splits(cohort)

        comparison = run_full_comparison(cohort)

        assert comparison.baseline is not None
        assert comparison.benchmark is None
        assert "no_alphaearth_features" in comparison.metadata.get("benchmark_skip_reason", "")

        report = generate_recommendation(comparison)
        assert report.recommendation == RECOMMENDATION_DEFER

    def test_workflow_report_persistence(self, tmp_path) -> None:
        """Benchmark report should persist to disk as markdown."""
        rng = np.random.default_rng(42)
        X = rng.random((100, 4))
        labels = ["species_a"] * 50 + ["species_b"] * 50

        builder = BenchmarkDatasetBuilder()
        cohort = builder.build_cohort("roi-persist", 2024, X, labels)
        cohort = builder.compute_splits(cohort)

        X_ae_train = rng.random((80, 64))
        X_ae_test = rng.random((20, 64))

        comparison = run_full_comparison(cohort, X_ae_train, X_ae_test)
        report = generate_recommendation(comparison)

        output = tmp_path / "benchmark-report.md"
        report.save(output)

        assert output.exists()
        content = output.read_text()
        assert "AlphaEarth Benchmark Report" in content
        assert report.recommendation in content
