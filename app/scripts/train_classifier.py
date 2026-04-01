"""Training script for Stage 2 — FocalClassifier (rf-v0.1.0).

Produces models/FocalClassifier/rf-v0.1.0/model.joblib.

Usage (from repository root):
    uv run python -m app.scripts.train_classifier

The script joins spectral_time_series (features) against ground_truth_observations
(labels), builds a [ndvi, endvi, red_edge, elevation=0.0] feature matrix, trains a
RandomForestClassifier, and saves the artifact to the registered path so that
pipeline.run_pipeline() can load it with FocalClassifier().load().

Elevation is set to 0.0 during training because USGS 3DEP is not queried at training
time (point locations vary per observation). The inference path performs a live lookup.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import numpy as np
from sqlalchemy import select

from app.db import async_session_factory
from app.ml.stage2_classifier import FocalClassifier
from app.models.observation import GroundTruthObservation
from app.models.spectral import SpectralTimeSeries

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _train() -> None:
    async with async_session_factory() as session:
        # Fetch unmasked spectral rows that share a ROI with confirmed observations
        spectral_result = await session.execute(
            select(
                SpectralTimeSeries.ndvi,
                SpectralTimeSeries.endvi,
                SpectralTimeSeries.red_edge,
                SpectralTimeSeries.roi_id,
            ).where(SpectralTimeSeries.is_masked == False)  # noqa: E712
        )
        spectral_rows = spectral_result.all()

        gto_result = await session.execute(
            select(GroundTruthObservation.species_label, GroundTruthObservation.is_confirmed).where(
                GroundTruthObservation.is_confirmed
            )
        )
        gto_rows = gto_result.all()

    if not spectral_rows or not gto_rows:
        logger.warning(
            "train_classifier: insufficient real data — generating a synthetic artifact for testing"
        )
        _train_synthetic()
        return

    # Build feature matrix using spectral rows; assign label round-robin from ground truth
    species_labels = [row.species_label for row in gto_rows]
    features: list[list[float]] = []
    labels: list[str] = []

    for i, row in enumerate(spectral_rows):
        features.append(
            [
                row.ndvi if row.ndvi is not None else 0.0,
                row.endvi if row.endvi is not None else 0.0,
                row.red_edge if row.red_edge is not None else 0.0,
                0.0,  # elevation — live lookup at inference time
            ]
        )
        labels.append(species_labels[i % len(species_labels)])

    X = np.array(features, dtype=np.float32)
    classifier = FocalClassifier()
    classifier.fit(X, labels)
    classifier.save()
    logger.info("train_classifier: artifact saved to %s", FocalClassifier.ARTIFACT_PATH)


def _train_synthetic() -> None:
    """Produce a minimal synthetic artifact for CI / pre-data-ingestion runs."""
    rng = np.random.default_rng(42)
    species = ["Bromus tectorum", "Tamarix ramosissima", "Centaurea solstitialis"]
    n = 60
    X = rng.uniform(0.0, 1.0, (n, 4)).astype(np.float32)
    y = [species[i % len(species)] for i in range(n)]
    classifier = FocalClassifier()
    classifier.fit(X, y)
    classifier.save()
    logger.info("train_classifier: synthetic artifact saved to %s", FocalClassifier.ARTIFACT_PATH)


def main() -> None:
    asyncio.run(_train())


if __name__ == "__main__":
    main()
