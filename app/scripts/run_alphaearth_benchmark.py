"""CLI entrypoint for Wave 1.5 AlphaEarth benchmark workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from uuid import UUID

from app.db import async_session_factory
from app.services.alphaearth_benchmark import run_matched_comparison
from app.services.alphaearth_client import AlphaEarthClient
from app.services.benchmark_dataset import assemble_benchmark_cohort
from app.services.benchmark_report import (
    DEFAULT_REPORT_PATH,
    generate_benchmark_recommendation,
    render_benchmark_report,
    write_benchmark_report,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wave 1.5 AlphaEarth benchmark runner")
    parser.add_argument(
        "--year",
        type=int,
        default=date.today().year,
        help="Target annual embedding year for access/coverage validation",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        default=False,
        help="Run only access/coverage and cohort assembly, skipping model comparison",
    )
    parser.add_argument(
        "--roi-id",
        type=UUID,
        help="Optional ROI UUID for cohort assembly and split alignment",
    )
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=0.2,
        help="Deterministic test split fraction for benchmark cohort assembly",
    )
    parser.add_argument(
        "--split-seed",
        type=int,
        default=42,
        help="Deterministic split seed for benchmark cohort assembly",
    )
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Markdown output path for the benchmark recommendation artifact",
    )
    return parser.parse_args()


async def _run() -> int:
    args = _parse_args()
    client = AlphaEarthClient()
    report_path = Path(args.report_path)

    # Wave 1.5 gate: non-blocking preflight to validate benchmark feasibility.
    result = await client.validate_annual_coverage(year=args.year)
    payload: dict[str, object] = {"validation": asdict(result)}
    cohort = None
    comparison = None
    workflow_reason: str | None = None

    if args.roi_id is not None and result.status == "ok":
        try:
            async with async_session_factory() as session:
                cohort = await assemble_benchmark_cohort(
                    session=session,
                    roi_id=args.roi_id,
                    year=args.year,
                    test_fraction=args.test_fraction,
                    split_seed=args.split_seed,
                )
            payload["cohort"] = {
                "roi_id": str(cohort.roi_id),
                "year": cohort.year,
                "sample_count": cohort.sample_count,
                "train_count": cohort.train_count,
                "test_count": cohort.test_count,
                "labels": cohort.labels,
            }

            if not args.validate_only:
                try:
                    comparison = run_matched_comparison(
                        cohort,
                        split_seed=args.split_seed,
                        coverage_ok=result.coverage_ok,
                    )
                except ValueError as exc:
                    workflow_reason = str(exc)
                    payload["comparison"] = {
                        "status": "skipped",
                        "reason": workflow_reason,
                    }
                else:
                    payload["comparison"] = comparison.to_dict()
            else:
                workflow_reason = "validate_only_requested"
        except ValueError as exc:
            workflow_reason = str(exc)
            payload["cohort"] = {
                "status": "skipped",
                "reason": workflow_reason,
            }

    recommendation = generate_benchmark_recommendation(
        validation=result,
        cohort=cohort,
        comparison=comparison,
        workflow_reason=workflow_reason,
        output_path=report_path,
    )
    report_markdown = render_benchmark_report(
        validation=result,
        recommendation=recommendation,
        cohort=cohort,
        comparison=comparison,
        workflow_reason=workflow_reason,
    )
    write_benchmark_report(output_path=report_path, markdown=report_markdown)
    payload["recommendation"] = recommendation.to_dict()
    payload["report_path"] = str(report_path)

    print(json.dumps(payload, indent=2, sort_keys=True))

    # Keep benchmark gating non-fatal: recommendations come from emitted status.
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
