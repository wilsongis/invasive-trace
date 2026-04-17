"""Training script for Stage 2 — FocalClassifier (rf-v0.1.0).

Produces models/FocalClassifier/rf-v0.1.0/classifier.pkl.

Usage (from repository root)::

    uv run python -m app.scripts.train_classifier \
        [--output-dir PATH] [--roi-ids UUID,UUID] [--force-retrain]

The script joins spectral_time_series (features) against ground_truth_observations
(labels), builds a 12-element temporal-aggregate feature matrix (NDVI/ENDVI/Red-Edge
min/max/mean/std), trains a RandomForestClassifier, and saves all artifacts to the
registered path so that pipeline.run_pipeline() can load it via FocalClassifier().load().
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import select

from app.db import async_session_factory
from app.ml.stage2_classifier import FocalClassifier
from app.models.observation import GroundTruthObservation
from app.services.feature_extractor import FeatureExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("invasive_trace.stage2")

OUTPUT_DIR = "models/FocalClassifier/rf-v0.1.0"


async def _train(output_dir: str, roi_ids_arg: list[str] | None, force_retrain: bool) -> None:
    """Main training coroutine."""
    skipped_invalid_features = 0
    skipped_low_scene_count = 0
    skipped_unknown_species = 0

    async with async_session_factory() as session:
        if roi_ids_arg:
            from uuid import UUID

            roi_ids = [UUID(r) for r in roi_ids_arg]
        else:
            # Auto-detect: all ROIs with at least one confirmed observation
            gto_query = (
                select(GroundTruthObservation.roi_id)
                .where(GroundTruthObservation.is_confirmed.is_(True))
                .distinct()
            )
            gto_result = await session.execute(gto_query)
            roi_ids = [row[0] for row in gto_result.all()]

    if not roi_ids:
        logger.warning(
            "train_classifier: no ROIs with confirmed observations — generating synthetic artifact"
        )
        _train_synthetic(output_dir)
        _print_run_summary(
            status="success",
            model_version=FocalClassifier.VERSION,
            sample_count=60,
            cv_f1_mean=None,
            cv_f1_std=None,
            test_f1=None,
            test_precision=None,
            test_recall=None,
            output_dir=output_dir,
            skipped_invalid=0,
            skipped_low_scene=0,
            skipped_unknown=0,
            note="synthetic",
        )
        return

    logger.info("Extracting training cohort for %d ROIs", len(roi_ids))
    training_cohort = await FeatureExtractor.extract_training_cohort(roi_ids)

    # Count records skipped during extraction (low-scene-count skip is logged inside
    # extract_training_cohort; we track what was accepted vs discarded here by comparing
    # with total confirmed observations).
    async with async_session_factory() as session:
        total_obs_query = select(GroundTruthObservation.id).where(
            GroundTruthObservation.is_confirmed.is_(True),
            GroundTruthObservation.roi_id.in_(roi_ids),
        )
        total_obs_result = await session.execute(total_obs_query)
        total_obs_count = len(total_obs_result.all())

    skipped_low_scene_count = total_obs_count - len(training_cohort)

    if not training_cohort:
        logger.warning(
            "train_classifier: no training data extracted — generating synthetic artifact"
        )
        _train_synthetic(output_dir)
        _print_run_summary(
            status="success",
            model_version=FocalClassifier.VERSION,
            sample_count=60,
            cv_f1_mean=None,
            cv_f1_std=None,
            test_f1=None,
            test_precision=None,
            test_recall=None,
            output_dir=output_dir,
            skipped_invalid=skipped_invalid_features,
            skipped_low_scene=skipped_low_scene_count,
            skipped_unknown=skipped_unknown_species,
            note="synthetic",
        )
        return

    logger.info("Training classifier with %d samples", len(training_cohort))
    try:
        result = FocalClassifier.train_classifier(
            training_cohort, output_dir, force_retrain=force_retrain
        )
    except Exception as exc:
        logger.error("Training failed: %s", exc)
        _print_run_summary(
            status="failure",
            model_version=FocalClassifier.VERSION,
            sample_count=len(training_cohort),
            cv_f1_mean=None,
            cv_f1_std=None,
            test_f1=None,
            test_precision=None,
            test_recall=None,
            output_dir=output_dir,
            skipped_invalid=skipped_invalid_features,
            skipped_low_scene=skipped_low_scene_count,
            skipped_unknown=skipped_unknown_species,
        )
        raise

    logger.info(
        "Training completed: samples=%d cv_f1=%.4f test_f1=%.4f",
        result.sample_count,
        float(np.mean(result.cv_scores)),
        result.test_f1,
    )

    # T032: Structured run logging
    logger.info(
        "stage2_train_summary",
        extra={
            "status": "success",
            "model_version": result.model_version,
            "training_date": datetime.now(tz=UTC).date().isoformat(),
            "training_sample_count": result.sample_count,
            "cv_f1_macro_mean": float(np.mean(result.cv_scores)),
            "cv_f1_macro_std": float(np.std(result.cv_scores)),
            "test_f1_macro": result.test_f1,
            "test_precision_macro": result.test_precision,
            "test_recall_macro": result.test_recall,
            "run_summary": {
                "skipped_invalid_features": skipped_invalid_features,
                "skipped_low_scene_count": skipped_low_scene_count,
                "skipped_unknown_species": skipped_unknown_species,
            },
        },
    )

    _print_run_summary(
        status="success",
        model_version=result.model_version,
        sample_count=result.sample_count,
        cv_f1_mean=float(np.mean(result.cv_scores)),
        cv_f1_std=float(np.std(result.cv_scores)),
        test_f1=result.test_f1,
        test_precision=result.test_precision,
        test_recall=result.test_recall,
        output_dir=output_dir,
        skipped_invalid=skipped_invalid_features,
        skipped_low_scene=skipped_low_scene_count,
        skipped_unknown=skipped_unknown_species,
    )


def _print_run_summary(
    *,
    status: str,
    model_version: str,
    sample_count: int,
    cv_f1_mean: float | None,
    cv_f1_std: float | None,
    test_f1: float | None,
    test_precision: float | None,
    test_recall: float | None,
    output_dir: str,
    skipped_invalid: int,
    skipped_low_scene: int,
    skipped_unknown: int,
    note: str | None = None,
) -> None:
    summary: dict = {
        "status": status,
        "model_version": model_version,
        "training_date": datetime.now(tz=UTC).date().isoformat(),
        "training_sample_count": sample_count,
        "cv_f1_macro_mean": cv_f1_mean,
        "cv_f1_macro_std": cv_f1_std,
        "test_f1_macro": test_f1,
        "test_precision_macro": test_precision,
        "test_recall_macro": test_recall,
        "run_summary": {
            "skipped_invalid_features": skipped_invalid,
            "skipped_low_scene_count": skipped_low_scene,
            "skipped_unknown_species": skipped_unknown,
        },
        "output_dir": output_dir,
    }
    if note:
        summary["note"] = note
    print(json.dumps(summary, indent=2))


def _train_synthetic(output_dir: str) -> None:
    """Produce a minimal synthetic artifact for CI / pre-data-ingestion runs."""
    from uuid import uuid4

    from app.services.feature_extractor import TrainingCohortRecord

    rng = np.random.default_rng(42)
    species = ["Bromus tectorum", "Tamarix ramosissima", "Centaurea solstitialis"]
    n = 60
    # Each of the 12 spectral aggregate features drawn from U(0, 1)
    raw = rng.uniform(0.0, 1.0, (n, 12)).astype(float)

    cohort = []
    dummy_roi = uuid4()
    for i in range(n):
        r = raw[i]
        cohort.append(
            TrainingCohortRecord(
                roi_id=dummy_roi,
                species_label=species[i % len(species)],
                ndvi_min=r[0],
                ndvi_max=r[1],
                ndvi_mean=r[2],
                ndvi_std=r[3],
                endvi_min=r[4],
                endvi_max=r[5],
                endvi_mean=r[6],
                endvi_std=r[7],
                red_edge_min=r[8],
                red_edge_max=r[9],
                red_edge_mean=r[10],
                red_edge_std=r[11],
            )
        )
    FocalClassifier.train_classifier(cohort, output_dir)
    logger.info("train_classifier: synthetic artifact saved to %s", output_dir)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Train Stage 2 FocalClassifier")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Artifact output directory")
    parser.add_argument(
        "--roi-ids",
        default=None,
        help="Comma-separated ROI UUIDs (auto-detect if omitted)",
    )
    parser.add_argument("--force-retrain", action="store_true", help="Overwrite existing artifact")
    args = parser.parse_args()

    roi_ids_arg = (
        [r.strip() for r in args.roi_ids.split(",") if r.strip()] if args.roi_ids else None
    )

    asyncio.run(_train(args.output_dir, roi_ids_arg, args.force_retrain))


if __name__ == "__main__":
    main()
