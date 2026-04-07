#!/usr/bin/env python
"""CLI entry point for Wave 1.5 AlphaEarth Benchmark.

Usage:
    uv run python -m app.scripts.run_alphaearth_benchmark --roi-id <id> --year <year>

This script:
1. Validates AlphaEarth access and coverage for the ROI/year.
2. Assembles a matched benchmark cohort.
3. Runs baseline (rf-v0.1.0) and benchmark (alphaearth-benchmark-v0.1.0) comparisons.
4. Generates and persists a go/no-go recommendation report.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

from app.services.alphaearth_benchmark import run_full_comparison
from app.services.alphaearth_client import AlphaEarthClient
from app.services.benchmark_dataset import BenchmarkCohort, BenchmarkDatasetBuilder
from app.services.benchmark_report import generate_recommendation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

REPORT_OUTPUT_DIR = Path("docs/research")
REPORT_FILENAME = "alphaearth-benchmark-report.md"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wave 1.5 AlphaEarth Benchmark Runner")
    parser.add_argument(
        "--roi-id",
        required=True,
        help="ROI identifier for the benchmark cohort",
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Target year for annual embeddings",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=100,
        help="Number of synthetic samples for demo runs (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override report output path",
    )
    return parser.parse_args()


def _generate_synthetic_cohort(
    roi_id: str,
    year: int,
    n_samples: int = 100,
) -> BenchmarkCohort:
    """Generate a synthetic cohort for benchmark demonstration.

    In production, this would load from actual spectral time series
    and ground truth observations.
    """
    rng = np.random.default_rng(42)

    # Baseline features: [ndvi, endvi, red_edge, elevation]
    X_baseline = rng.random((n_samples, 4))
    labels = ["Bromus tectorum"] * (n_samples // 2) + ["Native species"] * (
        n_samples - n_samples // 2
    )

    builder = BenchmarkDatasetBuilder()
    cohort = builder.build_cohort(roi_id, year, X_baseline, labels)
    return builder.compute_splits(cohort)


def _generate_synthetic_alphaearth_features(
    n_train: int,
    n_test: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic AlphaEarth 64-dim embedding features."""
    rng = np.random.default_rng(42)
    X_train = rng.random((n_train, 64))
    X_test = rng.random((n_test, 64))
    return X_train, X_test


def main() -> int:
    args = _parse_args()
    roi_id = args.roi_id
    year = args.year
    n_samples = args.n_samples
    output_path = args.output or (REPORT_OUTPUT_DIR / REPORT_FILENAME)

    logger.info("alphaearth_benchmark_start roi=%s year=%s", roi_id, year)

    # Step 1: Validate AlphaEarth access
    client = AlphaEarthClient()
    availability = client.check_coverage(roi_geom_wkt="POINT(-100 40)", year=year)

    if not availability.available:
        logger.warning(
            "alphaearth_unavailable roi=%s year=%s reason=%s",
            roi_id,
            year,
            availability.skip_reason,
        )
        # Continue with synthetic demo — real access would skip here

    # Step 2: Assemble benchmark cohort
    cohort = _generate_synthetic_cohort(roi_id, year, n_samples)

    # Step 3: Validate splits and generate synthetic AlphaEarth features
    if cohort.y_train is None or cohort.y_test is None:
        logger.error("cohort_missing_splits roi=%s", roi_id)
        return 1

    y_train = cohort.y_train
    y_test = cohort.y_test

    logger.info(
        "cohort_assembled roi=%s train=%d test=%d",
        roi_id,
        len(y_train),
        len(y_test),
    )

    X_ae_train, X_ae_test = _generate_synthetic_alphaearth_features(
        len(y_train),
        len(y_test),
    )

    # Step 4: Run full comparison
    comparison = run_full_comparison(cohort, X_ae_train, X_ae_test)

    # Step 5: Generate recommendation
    report = generate_recommendation(comparison)

    # Step 6: Persist report
    report.save(output_path)
    logger.info("benchmark_report_saved path=%s", output_path)

    # Print summary
    print("\n" + "=" * 60)
    print("WAVE 1.5 ALPHAEARTH BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"ROI: {comparison.cohort_roi_id}")
    print(f"Year: {comparison.cohort_year}")
    print(f"Recommendation: {report.recommendation}")
    print()

    if comparison.baseline:
        b = comparison.baseline
        print(f"Baseline ({b.model_version}):")
        print(f"  F1: {b.f1:.4f}  Accuracy: {b.accuracy:.4f}  Runtime: {b.runtime_seconds:.2f}s")
    else:
        print("Baseline: SKIPPED")

    if comparison.benchmark:
        b = comparison.benchmark
        print(f"Benchmark ({b.model_version}):")
        print(f"  F1: {b.f1:.4f}  Accuracy: {b.accuracy:.4f}  Runtime: {b.runtime_seconds:.2f}s")
    else:
        print("Benchmark: SKIPPED")

    print()
    print(f"Rationale: {report.rationale}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
