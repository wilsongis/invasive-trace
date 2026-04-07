"""Benchmark recommendation and report generation.

This module produces an auditable go/no-go recommendation artifact
from benchmark comparison results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.services.alphaearth_benchmark import BenchmarkComparison

logger = logging.getLogger(__name__)

RECOMMENDATION_GO = "go"
RECOMMENDATION_NO_GO = "no-go"
RECOMMENDATION_DEFER = "defer-for-further-research"


@dataclass
class BenchmarkReport:
    """Auditable benchmark recommendation report."""

    comparison: BenchmarkComparison
    recommendation: str
    rationale: str
    generated_at: str
    evidence_paths: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the report as a markdown artifact."""
        lines = [
            "# AlphaEarth Benchmark Report",
            "",
            f"**Generated**: {self.generated_at}",
            f"**Recommendation**: {self.recommendation}",
            "",
            "## Cohort",
            "",
            f"- **ROI ID**: {self.comparison.cohort_roi_id}",
            f"- **Year**: {self.comparison.cohort_year}",
            "",
            "## Baseline Results (rf-v0.1.0)",
            "",
        ]

        if self.comparison.baseline:
            b = self.comparison.baseline
            lines += [
                f"- **Precision**: {b.precision:.4f}",
                f"- **Recall**: {b.recall:.4f}",
                f"- **F1**: {b.f1:.4f}",
                f"- **Accuracy**: {b.accuracy:.4f}",
                f"- **Runtime**: {b.runtime_seconds:.2f}s",
                f"- **Train/Test**: {b.n_train}/{b.n_test}",
            ]
        else:
            lines.append("- *Baseline run skipped*")
            reason = self.comparison.metadata.get("baseline_skip_reason", "unknown")
            lines.append(f"  - Reason: {reason}")

        lines += [
            "",
            "## Benchmark Results (alphaearth-benchmark-v0.1.0)",
            "",
        ]

        if self.comparison.benchmark:
            b = self.comparison.benchmark
            lines += [
                f"- **Precision**: {b.precision:.4f}",
                f"- **Recall**: {b.recall:.4f}",
                f"- **F1**: {b.f1:.4f}",
                f"- **Accuracy**: {b.accuracy:.4f}",
                f"- **Runtime**: {b.runtime_seconds:.2f}s",
                f"- **Train/Test**: {b.n_train}/{b.n_test}",
            ]
        else:
            lines.append("- *Benchmark run skipped*")
            reason = self.comparison.metadata.get("benchmark_skip_reason", "unknown")
            lines.append(f"  - Reason: {reason}")

        lines += [
            "",
            "## Operational Findings",
            "",
            f"- **Dependency Burden**: {self.comparison.dependency_burden or 'N/A'}",
            f"- **Coverage Findings**: {self.comparison.coverage_findings or 'N/A'}",
            "",
            "## Rationale",
            "",
            self.rationale,
            "",
            "## Evidence Paths",
            "",
        ]

        for p in self.evidence_paths:
            lines.append(f"- `{p}`")

        if not self.evidence_paths:
            lines.append("- *No additional evidence paths*")

        lines.append("")
        return "\n".join(lines)

    def save(self, output_path: Path) -> None:
        """Persist the report to a markdown file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_markdown())
        logger.info("benchmark_report_saved path=%s", output_path)


def generate_recommendation(comparison: BenchmarkComparison) -> BenchmarkReport:
    """Generate a go/no-go recommendation from benchmark results.

    Decision logic:
    - If benchmark F1 > baseline F1 by >= 0.05 and runtime is comparable: go
    - If benchmark F1 <= baseline F1 or runtime is significantly worse: no-go
    - If either run was skipped: defer
    """
    baseline = comparison.baseline
    benchmark = comparison.benchmark

    if baseline is None or benchmark is None:
        recommendation = RECOMMENDATION_DEFER
        rationale = (
            "Insufficient evidence for a definitive recommendation. "
            "One or both comparison runs were skipped. "
            "Re-run the benchmark when AlphaEarth access and coverage are confirmed."
        )
    else:
        f1_delta = benchmark.f1 - baseline.f1
        runtime_ratio = (
            benchmark.runtime_seconds / baseline.runtime_seconds
            if baseline.runtime_seconds > 0
            else float("inf")
        )

        if f1_delta >= 0.05 and runtime_ratio <= 2.0:
            recommendation = RECOMMENDATION_GO
            rationale = (
                f"AlphaEarth benchmark shows meaningful improvement "
                f"(F1 delta: +{f1_delta:.4f}) with acceptable runtime overhead "
                f"({runtime_ratio:.1f}x baseline). "
                f"Recommend further evaluation for production integration."
            )
        elif f1_delta < 0:
            recommendation = RECOMMENDATION_NO_GO
            rationale = (
                f"AlphaEarth benchmark underperforms the baseline "
                f"(F1 delta: {f1_delta:.4f}). "
                f"Do not adopt AlphaEarth embeddings for production Stage 2."
            )
        else:
            recommendation = RECOMMENDATION_DEFER
            rationale = (
                f"AlphaEarth benchmark shows marginal improvement "
                f"(F1 delta: +{f1_delta:.4f}) but does not meet the "
                f"threshold for production adoption. "
                f"Consider further research with larger cohorts."
            )

    report = BenchmarkReport(
        comparison=comparison,
        recommendation=recommendation,
        rationale=rationale,
        generated_at=datetime.now(UTC).isoformat(),
    )

    logger.info(
        "benchmark_recommendation recommendation=%s f1_delta=%s",
        recommendation,
        f1_delta if baseline and benchmark else "N/A",
    )

    return report
