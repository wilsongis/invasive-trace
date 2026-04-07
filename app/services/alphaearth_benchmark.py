"""Benchmark orchestration: baseline vs AlphaEarth comparison.

This module runs the Stage 2 baseline (rf-v0.1.0) and the AlphaEarth
benchmark variant (alphaearth-benchmark-v0.1.0) on identical cohorts
and records side-by-side metrics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np

from app.ml.stage2_alphaearth_benchmark import AlphaEarthStage2Benchmark
from app.ml.stage2_classifier import FocalClassifier
from app.services.benchmark_dataset import BenchmarkCohort

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetrics:
    """Evaluation metrics for a single model variant."""

    model_version: str
    precision: float
    recall: float
    f1: float
    accuracy: float
    runtime_seconds: float
    n_train: int
    n_test: int


@dataclass
class BenchmarkComparison:
    """Side-by-side comparison of baseline and benchmark variants."""

    cohort_roi_id: str
    cohort_year: int
    baseline: BenchmarkMetrics | None = None
    benchmark: BenchmarkMetrics | None = None
    dependency_burden: str = ""
    coverage_findings: str = ""
    recommendation: str = ""
    metadata: dict = field(default_factory=dict)


def _compute_metrics(
    model,
    X_test: np.ndarray,
    y_test: list[str],
    runtime_seconds: float,
) -> BenchmarkMetrics:
    """Compute precision, recall, F1, accuracy for a fitted model."""
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    y_pred = []
    for i in range(len(X_test)):
        label, _ = model.predict(X_test[i : i + 1])
        y_pred.append(label)

    # Handle single-class edge case
    unique_labels = sorted(set(y_test))
    if len(unique_labels) < 2:
        precision = 1.0 if y_pred == y_test else 0.0
        recall = precision
        f1 = precision
    else:
        precision = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        recall = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
        f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    accuracy = float(accuracy_score(y_test, y_pred))

    return BenchmarkMetrics(
        model_version=model.VERSION,
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
        runtime_seconds=runtime_seconds,
        n_train=0,  # Set by caller
        n_test=len(y_test),
    )


def run_baseline_comparison(
    cohort: BenchmarkCohort,
) -> BenchmarkMetrics:
    """Train and evaluate the Stage 2 baseline on the cohort.

    Args:
        cohort: A BenchmarkCohort with train/test splits computed.

    Returns:
        BenchmarkMetrics for the baseline classifier.
    """
    if not cohort.is_split:
        raise ValueError("Cohort must have train/test splits computed")
    if cohort.X_train is None or cohort.y_train is None:
        raise ValueError("Cohort X_train/y_train must be set")
    if cohort.X_test is None or cohort.y_test is None:
        raise ValueError("Cohort X_test/y_test must be set")

    logger.info("baseline_comparison_start version=%s", FocalClassifier.VERSION)

    start = time.monotonic()
    model = FocalClassifier()
    model.fit(cohort.X_train, cohort.y_train)
    runtime = time.monotonic() - start

    metrics = _compute_metrics(model, cohort.X_test, cohort.y_test, runtime)
    metrics.n_train = len(cohort.y_train)

    logger.info(
        "baseline_comparison_complete f1=%.4f accuracy=%.4f runtime=%.2fs",
        metrics.f1,
        metrics.accuracy,
        metrics.runtime_seconds,
    )

    return metrics


def run_benchmark_comparison(
    cohort: BenchmarkCohort,
    X_alphaearth_train: np.ndarray,
    X_alphaearth_test: np.ndarray,
) -> BenchmarkMetrics:
    """Train and evaluate the AlphaEarth benchmark variant on the cohort.

    Args:
        cohort: A BenchmarkCohort with train/test splits computed.
        X_alphaearth_train: AlphaEarth embedding features for training.
        X_alphaearth_test: AlphaEarth embedding features for testing.

    Returns:
        BenchmarkMetrics for the benchmark classifier.
    """
    if not cohort.is_split:
        raise ValueError("Cohort must have train/test splits computed")
    if cohort.y_train is None or cohort.y_test is None:
        raise ValueError("Cohort y_train/y_test must be set")

    logger.info(
        "benchmark_comparison_start version=%s",
        AlphaEarthStage2Benchmark.VERSION,
    )

    start = time.monotonic()
    model = AlphaEarthStage2Benchmark()
    model.fit(X_alphaearth_train, cohort.y_train)
    runtime = time.monotonic() - start

    metrics = _compute_metrics(model, X_alphaearth_test, cohort.y_test, runtime)
    metrics.n_train = len(cohort.y_train)

    logger.info(
        "benchmark_comparison_complete f1=%.4f accuracy=%.4f runtime=%.2fs",
        metrics.f1,
        metrics.accuracy,
        metrics.runtime_seconds,
    )

    return metrics


def run_full_comparison(
    cohort: BenchmarkCohort,
    X_alphaearth_train: np.ndarray | None = None,
    X_alphaearth_test: np.ndarray | None = None,
) -> BenchmarkComparison:
    """Run both baseline and benchmark variants and produce a comparison.

    Args:
        cohort: A BenchmarkCohort with train/test splits computed.
        X_alphaearth_train: Optional AlphaEarth training features.
        X_alphaearth_test: Optional AlphaEarth test features.

    Returns:
        BenchmarkComparison with both metrics populated (or None if skipped).
    """
    comparison = BenchmarkComparison(
        cohort_roi_id=cohort.roi_id,
        cohort_year=cohort.year,
    )

    # Run baseline
    try:
        comparison.baseline = run_baseline_comparison(cohort)
    except Exception as exc:
        logger.warning("baseline_run_skip error=%s", exc)
        comparison.metadata["baseline_skip_reason"] = str(exc)

    # Run benchmark (only if AlphaEarth features provided)
    if X_alphaearth_train is not None and X_alphaearth_test is not None:
        try:
            comparison.benchmark = run_benchmark_comparison(
                cohort, X_alphaearth_train, X_alphaearth_test
            )
        except Exception as exc:
            logger.warning("benchmark_run_skip error=%s", exc)
            comparison.metadata["benchmark_skip_reason"] = str(exc)
    else:
        logger.info("benchmark_run_skipped reason=no_alphaearth_features")
        comparison.metadata["benchmark_skip_reason"] = "no_alphaearth_features"

    return comparison
