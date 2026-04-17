"""Wave 1.5 matched baseline-vs-AlphaEarth benchmark orchestration."""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

from app.ml.stage2_alphaearth_benchmark import AlphaEarthStage2Benchmark
from app.services.benchmark_dataset import BenchmarkCohort, BenchmarkSample


@dataclass(slots=True)
class VariantMetrics:
    """Summary metrics for one evaluated variant."""

    variant: str
    model_version: str
    precision: float
    recall: float
    f1: float
    runtime_seconds: float
    train_count: int
    test_count: int


@dataclass(slots=True)
class BenchmarkComparison:
    """Matched comparison output between baseline and AlphaEarth benchmark variants."""

    roi_id: str
    year: int
    labels: list[str]
    split_seed: int
    sample_count: int
    train_count: int
    test_count: int
    coverage_ok: bool
    dependency_burden: str
    baseline: VariantMetrics
    alphaearth: VariantMetrics

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable dictionary payload."""
        return {
            "roi_id": self.roi_id,
            "year": self.year,
            "labels": self.labels,
            "split_seed": self.split_seed,
            "sample_count": self.sample_count,
            "train_count": self.train_count,
            "test_count": self.test_count,
            "coverage_ok": self.coverage_ok,
            "dependency_burden": self.dependency_burden,
            "baseline": asdict(self.baseline),
            "alphaearth": asdict(self.alphaearth),
        }


def run_matched_comparison(
    cohort: BenchmarkCohort,
    *,
    split_seed: int,
    coverage_ok: bool,
) -> BenchmarkComparison:
    """Evaluate baseline and benchmark variants on identical cohort splits."""
    train_samples = [sample for sample in cohort.samples if sample.split == "train"]
    test_samples = [sample for sample in cohort.samples if sample.split == "test"]

    if not train_samples:
        raise ValueError("Benchmark cohort has no training samples")
    if not test_samples:
        raise ValueError("Benchmark cohort has no test samples")

    baseline_metrics = _evaluate_baseline(
        train_samples=train_samples,
        test_samples=test_samples,
    )
    alphaearth_metrics = _evaluate_alphaearth(
        train_samples=train_samples,
        test_samples=test_samples,
    )

    return BenchmarkComparison(
        roi_id=str(cohort.roi_id),
        year=cohort.year,
        labels=cohort.labels,
        split_seed=split_seed,
        sample_count=cohort.sample_count,
        train_count=cohort.train_count,
        test_count=cohort.test_count,
        coverage_ok=coverage_ok,
        dependency_burden=(
            "experimental-earth-engine-auth-and-coverage-dependency"
            if coverage_ok
            else "coverage-unavailable"
        ),
        baseline=baseline_metrics,
        alphaearth=alphaearth_metrics,
    )


def _evaluate_baseline(
    *,
    train_samples: list[BenchmarkSample],
    test_samples: list[BenchmarkSample],
) -> VariantMetrics:
    X_train = np.vstack([_baseline_features(sample) for sample in train_samples])
    X_test = np.vstack([_baseline_features(sample) for sample in test_samples])
    y_train = [sample.species_label for sample in train_samples]
    y_test = [sample.species_label for sample in test_samples]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    start = time.perf_counter()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    runtime_seconds = time.perf_counter() - start

    return VariantMetrics(
        variant="baseline",
        model_version="rf-v0.1.0",
        precision=float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
        recall=float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
        f1=float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        runtime_seconds=runtime_seconds,
        train_count=len(train_samples),
        test_count=len(test_samples),
    )


def _evaluate_alphaearth(
    *,
    train_samples: list[BenchmarkSample],
    test_samples: list[BenchmarkSample],
) -> VariantMetrics:
    X_train = np.vstack([_embedding_features(sample) for sample in train_samples])
    X_test = np.vstack([_embedding_features(sample) for sample in test_samples])
    y_train = [sample.species_label for sample in train_samples]
    y_test = [sample.species_label for sample in test_samples]

    model = AlphaEarthStage2Benchmark()
    start = time.perf_counter()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    runtime_seconds = time.perf_counter() - start

    return VariantMetrics(
        variant="alphaearth-benchmark",
        model_version=AlphaEarthStage2Benchmark.VERSION,
        precision=float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
        recall=float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
        f1=float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        runtime_seconds=runtime_seconds,
        train_count=len(train_samples),
        test_count=len(test_samples),
    )


def _baseline_features(sample: BenchmarkSample) -> np.ndarray:
    """Build a deterministic 4D baseline vector from observation coordinates."""
    lon_scaled = sample.lon / 180.0
    lat_scaled = sample.lat / 90.0
    trig_lon = float(np.sin(np.radians(sample.lon)))
    trig_lat = float(np.cos(np.radians(sample.lat)))
    return np.array([lon_scaled, lat_scaled, trig_lon, trig_lat], dtype=np.float32)


def _embedding_features(sample: BenchmarkSample, *, dimensions: int = 64) -> np.ndarray:
    """Derive deterministic pseudo-embedding vectors keyed by observation identity.

    Wave 1.5 uses this deterministic stand-in to exercise the matched evaluation
    pipeline while benchmark data plumbing is still evolving.
    """
    values: list[float] = []
    seed = str(sample.observation_id)
    for index in range(dimensions):
        digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
        # Convert first four bytes to a stable float in [-1.0, 1.0].
        raw = int.from_bytes(digest[:4], byteorder="big", signed=False)
        scaled = (raw / 0xFFFFFFFF) * 2.0 - 1.0
        values.append(scaled)
    return np.array(values, dtype=np.float32)
