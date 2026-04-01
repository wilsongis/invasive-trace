"""Wave 3 pipeline orchestrator: Stage 1 → Stage 2 → Stage 3.

run_pipeline() chains AnomalyDetector → FocalClassifier → UNetTexture for a given
ROI, persists invasion_predictions rows, emits lineage logs, and returns a
PipelineRunResponse summary.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from uuid import UUID

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.stage1_anomaly import AnomalyDetector
from app.ml.stage2_classifier import FocalClassifier
from app.ml.stage3_unet import UNetTexture, extract_sentinel2_patch
from app.models.prediction import InvasionPrediction
from app.models.roi import RegionOfInterest
from app.models.spectral import SpectralTimeSeries
from app.schemas.pipeline import PipelineRunResponse
from app.services.feature_extractor import build_feature_vector
from app.services.ml_runtime import (
    STAGE1_VERSION,
    STAGE2_VERSION,
    STAGE3_VERSION,
    clamp_confidence,
    clamp_hotspot_score,
)

logger = logging.getLogger(__name__)


class ROINotFoundError(ValueError):
    """Raised when the target ROI does not exist in the database."""


async def run_pipeline(roi_id: UUID, db: AsyncSession) -> PipelineRunResponse:
    """Execute the full three-stage AI chain for a given ROI.

    Stages are chained in strict order: Stage 1 → Stage 2 → Stage 3.
    Model artifacts are loaded before stage execution so that a missing artifact
    fails fast before any prediction row is written.

    Args:
        roi_id: UUID of the target RegionOfInterest.
        db: Async SQLAlchemy session (provided by FastAPI dependency injection).

    Returns:
        PipelineRunResponse with roi_id, predictions_created, model_version, message.

    Raises:
        ROINotFoundError: When the ROI does not exist.
        AnomalyDetectorArtifactMissingError: Stage 1 artifact missing.
        FocalClassifierArtifactMissingError: Stage 2 artifact missing.
        UNetTextureArtifactMissingError: Stage 3 artifact missing.
    """
    # ------------------------------------------------------------------
    # Fetch ROI
    # ------------------------------------------------------------------
    roi = await db.get(RegionOfInterest, roi_id)
    if roi is None:
        raise ROINotFoundError(f"ROI {roi_id} not found")

    # Derive detection point: centroid of the ROI polygon in WGS84 (FR-022a)
    roi_shape = to_shape(roi.geom)
    centroid = roi_shape.centroid
    lon, lat = centroid.x, centroid.y

    # ------------------------------------------------------------------
    # Load unmasked spectral rows (IS_MASKED = FALSE)
    # ------------------------------------------------------------------
    result = await db.execute(
        select(SpectralTimeSeries)
        .where(SpectralTimeSeries.roi_id == roi_id)
        .where(SpectralTimeSeries.is_masked.is_(False))
        .order_by(SpectralTimeSeries.scene_date)
    )
    spectral_rows = result.scalars().all()

    if not spectral_rows:
        logger.info("pipeline_no_usable_spectral roi_id=%s", roi_id)
        return PipelineRunResponse(
            roi_id=roi_id,
            predictions_created=0,
            model_version=STAGE2_VERSION,
            message="No unmasked spectral data available for this ROI.",
        )

    # ------------------------------------------------------------------
    # Eager artifact load — fail fast before any DB write (SC-008)
    # ------------------------------------------------------------------
    stage1 = AnomalyDetector().load()
    stage2 = FocalClassifier().load()
    stage3 = UNetTexture().load()

    # ------------------------------------------------------------------
    # Stage 1: Anomaly detection on NDVI time series
    # ------------------------------------------------------------------
    ndvi_series = [(row.scene_date, row.ndvi) for row in spectral_rows if row.ndvi is not None]

    if not ndvi_series:
        logger.info("pipeline_no_ndvi_values roi_id=%s", roi_id)
        return PipelineRunResponse(
            roi_id=roi_id,
            predictions_created=0,
            model_version=STAGE2_VERSION,
            message="No NDVI values available for anomaly detection.",
        )

    logger.info(
        "pipeline_stage1_start version=%s roi_id=%s n_scenes=%d",
        STAGE1_VERSION,
        roi_id,
        len(ndvi_series),
    )
    anomalies = stage1.predict(ndvi_series)

    if not anomalies:
        logger.info("pipeline_no_anomalies roi_id=%s", roi_id)
        return PipelineRunResponse(
            roi_id=roi_id,
            predictions_created=0,
            model_version=STAGE2_VERSION,
            message="Stage 1 detected no anomalous scenes in the NDVI time series.",
        )

    # Build a lookup from scene_date → spectral row for Stage 2/3 data access
    scene_by_date: dict[date, SpectralTimeSeries] = {row.scene_date: row for row in spectral_rows}

    # ------------------------------------------------------------------
    # Per-anomaly: Stage 2 + Stage 3 → write prediction
    # ------------------------------------------------------------------
    predictions_created = 0

    for scene_date, _departure_score in anomalies:
        row = scene_by_date.get(scene_date)
        if row is None:
            continue

        # Stage 2: feature vector + classify
        feature_vec = await build_feature_vector(
            ndvi=row.ndvi,
            endvi=row.endvi,
            red_edge=row.red_edge,
            lon=lon,
            lat=lat,
        )
        species_label, raw_confidence = stage2.predict(feature_vec)
        confidence = clamp_confidence(raw_confidence)

        logger.info(
            "pipeline_stage2 version=%s roi_id=%s scene_date=%s species=%s confidence=%.4f",
            STAGE2_VERSION,
            roi_id,
            scene_date,
            species_label,
            confidence,
        )

        # Stage 3: patch extraction + hotspot scoring
        patch = await extract_sentinel2_patch(
            stac_item_id=row.stac_item,
            lon=lon,
            lat=lat,
        )

        hotspot_score: float | None = None
        if patch is not None:
            raw_hotspot = stage3.infer(patch)
            hotspot_score = clamp_hotspot_score(raw_hotspot)
            logger.info(
                "pipeline_stage3 version=%s roi_id=%s scene_date=%s hotspot=%.4f",
                STAGE3_VERSION,
                roi_id,
                scene_date,
                hotspot_score,
            )
        else:
            logger.warning(
                "pipeline_stage3_skipped roi_id=%s scene_date=%s reason=stac_unavailable",
                roi_id,
                scene_date,
            )

        # Persist prediction (validated=NULL, validator_notes=NULL by default)
        pred = InvasionPrediction(
            roi_id=roi_id,
            species_label=species_label,
            confidence=confidence,
            hotspot_score=hotspot_score,
            geom=from_shape(Point(lon, lat), srid=4326),
            model_version=STAGE2_VERSION,
            validated=None,
            validator_notes=None,
        )
        db.add(pred)
        predictions_created += 1

    await db.commit()

    # ------------------------------------------------------------------
    # Lineage log + per-run sidecar metadata (FR-020, SC-009)
    # ------------------------------------------------------------------
    sidecar = {
        "roi_id": str(roi_id),
        "predictions_created": predictions_created,
        "stage1_version": STAGE1_VERSION,
        "stage2_version": STAGE2_VERSION,
        "stage3_version": STAGE3_VERSION,
    }
    logger.info("pipeline_lineage %s", json.dumps(sidecar))

    message = (
        f"Pipeline completed. {predictions_created} prediction(s) created."
        if predictions_created > 0
        else "Pipeline completed with no predictions."
    )

    return PipelineRunResponse(
        roi_id=roi_id,
        predictions_created=predictions_created,
        model_version=STAGE2_VERSION,
        message=message,
    )
