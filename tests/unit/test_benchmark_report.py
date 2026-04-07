"""Unit tests for benchmark report generation."""

from __future__ import annotations

from pathlib import Path

from app.services.alphaearth_benchmark import BenchmarkComparison, BenchmarkMetrics
from app.services.benchmark_report import (
    RECOMMENDATION_DEFER,
    RECOMMENDATION_GO,
    RECOMMENDATION_NO_GO,
    generate_recommendation,
)


def _make_comparison(
    baseline_f1: float = 0.80,
    benchmark_f1: float = 0.85,
    baseline_runtime: float = 1.0,
    benchmark_runtime: float = 1.5,
    baseline_skipped: bool = False,
    benchmark_skipped: bool = False,
) -> BenchmarkComparison:
    """Helper to create a BenchmarkComparison with given metrics."""
    baseline = (
        None
        if baseline_skipped
        else BenchmarkMetrics(
            model_version="rf-v0.1.0",
            precision=0.80,
            recall=0.80,
            f1=baseline_f1,
            accuracy=0.80,
            runtime_seconds=baseline_runtime,
            n_train=80,
            n_test=20,
        )
    )
    benchmark = (
        None
        if benchmark_skipped
        else BenchmarkMetrics(
            model_version="alphaearth-benchmark-v0.1.0",
            precision=0.85,
            recall=0.85,
            f1=benchmark_f1,
            accuracy=0.85,
            runtime_seconds=benchmark_runtime,
            n_train=80,
            n_test=20,
        )
    )
    return BenchmarkComparison(
        cohort_roi_id="roi-1",
        cohort_year=2024,
        baseline=baseline,
        benchmark=benchmark,
    )


class TestBenchmarkReport:
    """Tests for benchmark report generation and recommendation logic."""

    def test_recommendation_go(self) -> None:
        """Should recommend go when benchmark F1 improves by >= 0.05."""
        comparison = _make_comparison(baseline_f1=0.80, benchmark_f1=0.86)
        report = generate_recommendation(comparison)

        assert report.recommendation == RECOMMENDATION_GO
        assert "meaningful improvement" in report.rationale

    def test_recommendation_no_go(self) -> None:
        """Should recommend no-go when benchmark underperforms."""
        comparison = _make_comparison(baseline_f1=0.80, benchmark_f1=0.75)
        report = generate_recommendation(comparison)

        assert report.recommendation == RECOMMENDATION_NO_GO
        assert "underperforms" in report.rationale

    def test_recommendation_defer_skipped(self) -> None:
        """Should recommend defer when either run was skipped."""
        comparison = _make_comparison(benchmark_skipped=True)
        report = generate_recommendation(comparison)

        assert report.recommendation == RECOMMENDATION_DEFER
        assert "Insufficient evidence" in report.rationale

    def test_recommendation_defer_marginal(self) -> None:
        """Should recommend defer for marginal improvement below threshold."""
        comparison = _make_comparison(baseline_f1=0.80, benchmark_f1=0.82)
        report = generate_recommendation(comparison)

        assert report.recommendation == RECOMMENDATION_DEFER
        assert "marginal improvement" in report.rationale

    def test_report_to_markdown(self) -> None:
        """Report should render as valid markdown."""
        comparison = _make_comparison()
        report = generate_recommendation(comparison)
        md = report.to_markdown()

        assert "# AlphaEarth Benchmark Report" in md
        assert "rf-v0.1.0" in md
        assert "alphaearth-benchmark-v0.1.0" in md
        assert report.recommendation in md

    def test_report_save(self, tmp_path: Path) -> None:
        """Report should persist to a markdown file."""
        comparison = _make_comparison()
        report = generate_recommendation(comparison)
        output = tmp_path / "test-report.md"

        report.save(output)

        assert output.exists()
        content = output.read_text()
        assert "# AlphaEarth Benchmark Report" in content

    def test_report_markdown_skipped_baseline(self) -> None:
        """Report should indicate skipped baseline in markdown."""
        comparison = _make_comparison(baseline_skipped=True)
        report = generate_recommendation(comparison)
        md = report.to_markdown()

        assert "Baseline run skipped" in md

    def test_report_markdown_skipped_benchmark(self) -> None:
        """Report should indicate skipped benchmark in markdown."""
        comparison = _make_comparison(benchmark_skipped=True)
        report = generate_recommendation(comparison)
        md = report.to_markdown()

        assert "Benchmark run skipped" in md
