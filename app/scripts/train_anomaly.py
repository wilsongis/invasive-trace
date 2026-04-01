"""Training script for Stage 1 — AnomalyDetector (anomaly-v0.1.0).

Produces models/AnomalyDetector/anomaly-v0.1.0/model.joblib.

Usage (from repository root):
    uv run python -m app.scripts.train_anomaly

The script queries spectral_time_series for all unmasked NDVI values, trains
an IsolationForest, and saves the artifact to the registered path so that
pipeline.run_pipeline() can load it with AnomalyDetector().load().
"""

from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy import select

from app.db import async_session_factory
from app.ml.stage1_anomaly import AnomalyDetector
from app.models.spectral import SpectralTimeSeries

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _train() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(SpectralTimeSeries.scene_date, SpectralTimeSeries.ndvi)
            .where(SpectralTimeSeries.is_masked == False)  # noqa: E712
            .where(SpectralTimeSeries.ndvi.is_not(None))
            .order_by(SpectralTimeSeries.scene_date)
        )
        rows = result.all()

    if not rows:
        # Produce a synthetic training set so the artifact can be generated
        # even when no spectral data has been ingested yet.
        logger.warning(
            "train_anomaly: no unmasked NDVI rows found — "
            "generating a synthetic artifact for testing"
        )
        from datetime import date  # noqa: PLC0415

        import numpy as np  # noqa: PLC0415

        rng = np.random.default_rng(42)
        synthetic = [(date(2024, i + 1, 1), float(rng.uniform(0.2, 0.8))) for i in range(36)]
        rows = [(d, v) for d, v in synthetic]

    tuples = [(d, float(v)) for d, v in rows]
    detector = AnomalyDetector()
    detector.fit(tuples)
    detector.save()
    logger.info("train_anomaly: artifact saved to %s", AnomalyDetector.ARTIFACT_PATH)


def main() -> None:
    asyncio.run(_train())


if __name__ == "__main__":
    main()
