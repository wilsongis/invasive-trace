"""Inference script for Stage 2 — FocalClassifier (rf-v0.1.0).

Usage (from repository root):
    uv run python -m app.scripts.run_stage2_inference \\
        --roi-ids "UUID1,UUID2" --model-version "rf-v0.1.0" [--dry-run]

For each ROI the script:
  1. Generates a deterministic 500-m grid of candidate locations.
  2. Extracts a 12-element temporal spectral feature vector per candidate.
  3. Classifies each with the trained FocalClassifier.
  4. Persists results in invasion_predictions (unless --dry-run).
  5. Prints a canonical JSON run_summary to stdout.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import UTC, datetime
from uuid import UUID

from app.ml.stage2_classifier import VERSION, FocalClassifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("invasive_trace.stage2")


async def run_inference(roi_ids: list[str], model_version: str, dry_run: bool = False) -> None:
    """Run inference on candidate locations for given ROIs, then emit a run_summary."""
    logger.info(
        "stage2_inference_start roi_count=%d model=%s dry_run=%s",
        len(roi_ids),
        model_version,
        dry_run,
    )
    global_start = time.monotonic()

    result = await FocalClassifier.infer_predictions(roi_ids, model_version, dry_run)

    total_time = time.monotonic() - global_start

    # Build per-ROI accounting from InferenceResult
    roi_results: list[dict] = []
    predictions_by_roi: dict[str, list] = {}
    for pred in result.predictions:
        predictions_by_roi.setdefault(pred["roi_id"], []).append(pred)

    for roi_id in roi_ids:
        preds = predictions_by_roi.get(roi_id, [])
        roi_results.append(
            {
                "roi_id": roi_id,
                "candidates_generated": 0,  # filled below if available
                "candidates_processed": len(preds),
                "predictions_written": len(preds) if not dry_run else 0,
                "skipped_invalid_features": 0,
                "inference_time_sec": result.total_time_sec / max(len(roi_ids), 1),
            }
        )

    total_predictions = sum(r["predictions_written"] for r in roi_results)

    summary = {
        "status": "success" if result.predictions else "partial",
        "model_version": model_version,
        "inference_date": datetime.now(tz=UTC).date().isoformat(),
        "run_summary": {
            "roi_results": roi_results,
            "total_predictions_written": total_predictions,
            "total_inference_time_sec": round(total_time, 4),
        },
    }
    print(json.dumps(summary, indent=2))

    logger.info(
        "stage2_inference_done roi_count=%d total_predictions=%d elapsed=%.2fs",
        len(roi_ids),
        len(result.predictions),
        total_time,
    )

    # T032: Structured run logging
    logger.info(
        "stage2_inference_summary",
        extra={
            "status": "success" if result.predictions else "partial",
            "model_version": model_version,
            "inference_date": datetime.now(tz=UTC).date().isoformat(),
            "run_summary": {
                "roi_results": roi_results,
                "total_predictions_written": total_predictions,
                "total_inference_time_sec": round(total_time, 4),
            },
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 2 FocalClassifier inference")
    parser.add_argument("--roi-ids", required=True, help="Comma-separated ROI UUIDs")
    parser.add_argument(
        "--model-version",
        default=VERSION,
        help=f"Model version to load (default: {VERSION})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip DB writes")
    args = parser.parse_args()

    roi_ids = [r.strip() for r in args.roi_ids.split(",") if r.strip()]
    if not roi_ids:
        logger.error("No ROI IDs provided")
        sys.exit(1)

    # Validate UUIDs early
    for r in roi_ids:
        try:
            UUID(r)
        except ValueError:
            logger.error("Invalid UUID: %s", r)
            sys.exit(1)

    asyncio.run(run_inference(roi_ids, args.model_version, args.dry_run))


if __name__ == "__main__":
    main()
