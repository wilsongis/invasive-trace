"""Unit tests for matched baseline-vs-AlphaEarth benchmark orchestration."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.alphaearth_benchmark import run_matched_comparison
from app.services.benchmark_dataset import BenchmarkCohort, BenchmarkSample


def _sample(*, split: str, species: str, lon: float, lat: float) -> BenchmarkSample:
    return BenchmarkSample(
        observation_id=uuid4(),
        species_label=species,
        lon=lon,
        lat=lat,
        split=split,
    )


def _cohort() -> BenchmarkCohort:
    samples = [
        _sample(split="train", species="Bromus tectorum", lon=-101.0, lat=35.0),
        _sample(split="train", species="Tamarix ramosissima", lon=-101.2, lat=35.1),
        _sample(split="train", species="Bromus tectorum", lon=-101.3, lat=35.2),
        _sample(split="test", species="Bromus tectorum", lon=-101.1, lat=35.05),
        _sample(split="test", species="Tamarix ramosissima", lon=-101.4, lat=35.3),
    ]
    return BenchmarkCohort(
        roi_id=uuid4(),
        year=2024,
        labels=["Bromus tectorum", "Tamarix ramosissima"],
        sample_count=len(samples),
        train_count=3,
        test_count=2,
        samples=samples,
    )


def test_run_matched_comparison_emits_both_variants_metrics() -> None:
    cohort = _cohort()

    result = run_matched_comparison(cohort, split_seed=42, coverage_ok=True)

    assert result.roi_id == str(cohort.roi_id)
    assert result.train_count == cohort.train_count
    assert result.test_count == cohort.test_count
    assert result.baseline.model_version == "rf-v0.1.0"
    assert result.alphaearth.model_version == "alphaearth-benchmark-v0.1.0"
    assert 0.0 <= result.baseline.precision <= 1.0
    assert 0.0 <= result.baseline.recall <= 1.0
    assert 0.0 <= result.baseline.f1 <= 1.0
    assert 0.0 <= result.alphaearth.precision <= 1.0
    assert 0.0 <= result.alphaearth.recall <= 1.0
    assert 0.0 <= result.alphaearth.f1 <= 1.0


def test_run_matched_comparison_raises_when_test_split_missing() -> None:
    bad_samples = [
        _sample(split="train", species="Bromus tectorum", lon=-101.0, lat=35.0),
        _sample(split="train", species="Tamarix ramosissima", lon=-101.2, lat=35.1),
    ]
    bad_cohort = BenchmarkCohort(
        roi_id=uuid4(),
        year=2024,
        labels=["Bromus tectorum", "Tamarix ramosissima"],
        sample_count=2,
        train_count=2,
        test_count=0,
        samples=bad_samples,
    )

    with pytest.raises(ValueError, match="no test samples"):
        run_matched_comparison(bad_cohort, split_seed=42, coverage_ok=False)
