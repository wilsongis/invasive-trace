"""Stage 2 feature vector assembly: spectral indices + resilient USGS 3DEP elevation."""

from __future__ import annotations

import logging
import random
import time
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import func, select, text

from app.db import async_session_factory
from app.models.observation import GroundTruthObservation
from app.models.roi import RegionOfInterest
from app.models.spectral import SpectralTimeSeries
from app.services.usgs_3dep_client import get_elevation

logger = logging.getLogger(__name__)

# Minimum unmasked scenes required per observation for a valid training record
MIN_SCENES = 3

# Temporal window half-width in days (±45 days around observation date)
TEMPORAL_WINDOW_DAYS = 45


class TrainingCohortRecord:
    """A training record for the Stage 2 classifier.

    Stores the 12 temporal aggregate spectral features (min/max/mean/std for
    NDVI, ENDVI, Red-Edge) for a single ground-truth observation.
    """

    def __init__(
        self,
        roi_id: UUID,
        species_label: str,
        ndvi_min: float,
        ndvi_max: float,
        ndvi_mean: float,
        ndvi_std: float,
        endvi_min: float,
        endvi_max: float,
        endvi_mean: float,
        endvi_std: float,
        red_edge_min: float,
        red_edge_max: float,
        red_edge_mean: float,
        red_edge_std: float,
    ):
        self.roi_id = roi_id
        self.species_label = species_label
        self.ndvi_min = ndvi_min
        self.ndvi_max = ndvi_max
        self.ndvi_mean = ndvi_mean
        self.ndvi_std = ndvi_std
        self.endvi_min = endvi_min
        self.endvi_max = endvi_max
        self.endvi_mean = endvi_mean
        self.endvi_std = endvi_std
        self.red_edge_min = red_edge_min
        self.red_edge_max = red_edge_max
        self.red_edge_mean = red_edge_mean
        self.red_edge_std = red_edge_std


class InferenceVector:
    """A 12-element feature vector for Stage 2 inference."""

    def __init__(
        self,
        ndvi_min: float,
        ndvi_max: float,
        ndvi_mean: float,
        ndvi_std: float,
        endvi_min: float,
        endvi_max: float,
        endvi_mean: float,
        endvi_std: float,
        red_edge_min: float,
        red_edge_max: float,
        red_edge_mean: float,
        red_edge_std: float,
    ):
        self.ndvi_min = ndvi_min
        self.ndvi_max = ndvi_max
        self.ndvi_mean = ndvi_mean
        self.ndvi_std = ndvi_std
        self.endvi_min = endvi_min
        self.endvi_max = endvi_max
        self.endvi_mean = endvi_mean
        self.endvi_std = endvi_std
        self.red_edge_min = red_edge_min
        self.red_edge_max = red_edge_max
        self.red_edge_mean = red_edge_mean
        self.red_edge_std = red_edge_std


class CandidateLocation:
    """A candidate location for Stage 2 inference."""

    def __init__(self, roi_id: UUID, geom: str, grid_row: int = 0, grid_col: int = 0):
        self.roi_id = roi_id
        self.geom = geom
        self.grid_row = grid_row
        self.grid_col = grid_col


class FeatureExtractor:
    """Extracts features for Stage 2 classifier training and inference."""

    @staticmethod
    async def extract_training_cohort(
        roi_ids: list[UUID], skip_reasons: dict[str, int] | None = None
    ) -> list[TrainingCohortRecord]:
        """Extract training cohort from ground truth observations and spectral time series.

        For each confirmed ground-truth observation, aggregate spectral indices over the
        ±TEMPORAL_WINDOW_DAYS (45-day) window of unmasked scenes centred on the observation
        date.  Requires at least MIN_SCENES (3) unmasked scenes; skips otherwise.

        Results are ordered by (roi_id, species_label, observation_date) for
        full reproducibility — same DB state always returns the same cohort.

        Args:
            roi_ids: List of ROI IDs to extract training data from.
            skip_reasons: Optional dict to accumulate skip counts by reason.

        Returns:
            List of TrainingCohortRecord objects, one per valid observation.
        """
        if skip_reasons is None:
            skip_reasons = {}

        async with async_session_factory() as session:
            # Fetch confirmed ground-truth observations for the target ROIs.
            # ORDER BY required for deterministic cohort — do not remove
            gto_query = (
                select(
                    GroundTruthObservation.id,
                    GroundTruthObservation.roi_id,
                    GroundTruthObservation.species_label,
                    GroundTruthObservation.observed_at,
                )
                .where(
                    GroundTruthObservation.is_confirmed.is_(True),
                    GroundTruthObservation.roi_id.in_(roi_ids),
                )
                .order_by(
                    GroundTruthObservation.roi_id,
                    GroundTruthObservation.species_label,
                    GroundTruthObservation.observed_at,
                )
            )
            gto_result = await session.execute(gto_query)
            gto_rows = gto_result.all()

            cohort: list[TrainingCohortRecord] = []
            for gto_row in gto_rows:
                roi_id = gto_row.roi_id
                species_label = gto_row.species_label
                observed_at = gto_row.observed_at

                # Build the temporal window filter (NULL observed_at → skip).
                if observed_at is None:
                    logger.warning(
                        "extract_training_cohort: skipping observation %s (no observed_at date)",
                        gto_row.id,
                    )
                    skip_reasons.setdefault("skipped_no_observed_at", 0)
                    skip_reasons["skipped_no_observed_at"] += 1
                    continue

                # Query unmasked spectral scenes within the ±45-day window.
                # T021: Enforce cloud-mask filter — is_masked = FALSE
                window_filter = text(
                    "ABS(EXTRACT(epoch FROM (scene_date - :obs_date)) / 86400) <= :window"
                )
                spectral_query = (
                    select(
                        SpectralTimeSeries.ndvi,
                        SpectralTimeSeries.endvi,
                        SpectralTimeSeries.red_edge,
                        SpectralTimeSeries.scene_date,
                    )
                    .where(
                        SpectralTimeSeries.roi_id == roi_id,
                        SpectralTimeSeries.is_masked.is_(False),  # T021: cloud-mask filter
                        window_filter,
                    )
                    .params(obs_date=observed_at, window=TEMPORAL_WINDOW_DAYS)
                )
                spectral_result = await session.execute(spectral_query)
                spectral_rows = spectral_result.all()

                # Only keep rows with all three spectral indices present.
                valid_rows = [
                    r
                    for r in spectral_rows
                    if r.ndvi is not None and r.endvi is not None and r.red_edge is not None
                ]

                # T020: Enforce minimum scene count
                if len(valid_rows) < MIN_SCENES:
                    logger.warning(
                        "extract_training_cohort: skipping observation %s "
                        "(only %d/%d valid scenes in ±%d-day window)",
                        gto_row.id,
                        len(valid_rows),
                        MIN_SCENES,
                        TEMPORAL_WINDOW_DAYS,
                    )
                    skip_reasons.setdefault("skipped_low_scene_count", 0)
                    skip_reasons["skipped_low_scene_count"] += 1
                    continue

                ndvi_vals = [r.ndvi for r in valid_rows]
                endvi_vals = [r.endvi for r in valid_rows]
                re_vals = [r.red_edge for r in valid_rows]

                def _stats(vals: list[float]) -> tuple[float, float, float, float]:
                    return (
                        float(min(vals)),
                        float(max(vals)),
                        float(np.mean(vals)),
                        float(np.std(vals)) if len(vals) > 1 else 0.0,
                    )

                ndvi_min, ndvi_max, ndvi_mean, ndvi_std = _stats(ndvi_vals)
                endvi_min, endvi_max, endvi_mean, endvi_std = _stats(endvi_vals)
                re_min, re_max, re_mean, re_std = _stats(re_vals)

                # T020: Validate feature vector before adding to cohort
                feature_values = [
                    ndvi_min,
                    ndvi_max,
                    ndvi_mean,
                    ndvi_std,
                    endvi_min,
                    endvi_max,
                    endvi_mean,
                    endvi_std,
                    red_edge_min := re_min,
                    red_edge_max := re_max,
                    red_edge_mean := re_mean,
                    red_edge_std := re_std,
                ]

                # Check all values are finite (no NaN or infinity)
                import math

                if not all(math.isfinite(v) for v in feature_values):
                    logger.warning(
                        "extract_training_cohort: skipping observation %s "
                        "(non-finite feature value detected)",
                        gto_row.id,
                    )
                    skip_reasons.setdefault("skipped_invalid_features", 0)
                    skip_reasons["skipped_invalid_features"] += 1
                    continue

                cohort.append(
                    TrainingCohortRecord(
                        roi_id=roi_id,
                        species_label=species_label,
                        ndvi_min=ndvi_min,
                        ndvi_max=ndvi_max,
                        ndvi_mean=ndvi_mean,
                        ndvi_std=ndvi_std,
                        endvi_min=endvi_min,
                        endvi_max=endvi_max,
                        endvi_mean=endvi_mean,
                        endvi_std=endvi_std,
                        red_edge_min=red_edge_min,
                        red_edge_max=red_edge_max,
                        red_edge_mean=red_edge_mean,
                        red_edge_std=red_edge_std,
                    )
                )

            return cohort

    @staticmethod
    async def extract_inference_vector(roi_id: UUID, candidate_geom: str) -> InferenceVector | None:
        """Extract a 12-element feature vector for inference from spectral time series.

        Args:
            roi_id: The ROI ID
            candidate_geom: The candidate location geometry

        Returns:
            InferenceVector with 12 features (min, max, mean, std for each of NDVI, ENDVI, Red-Edge)
        """
        async with async_session_factory() as session:
            # Query spectral time series for this ROI with unmasked scenes
            query = select(
                SpectralTimeSeries.ndvi, SpectralTimeSeries.endvi, SpectralTimeSeries.red_edge
            ).where(~SpectralTimeSeries.is_masked, SpectralTimeSeries.roi_id == roi_id)

            result = await session.execute(query)
            rows = result.all()

            # If no data, return None
            if not rows:
                return None

            # Extract features
            ndvi_values = [row.ndvi for row in rows if row.ndvi is not None]
            endvi_values = [row.endvi for row in rows if row.endvi is not None]
            red_edge_values = [row.red_edge for row in rows if row.red_edge is not None]

            # Check if we have enough data
            if len(ndvi_values) < 3 or len(endvi_values) < 3 or len(red_edge_values) < 3:
                return None

            # Compute aggregates
            def compute_stats(values):
                if not values:
                    return 0.0, 0.0, 0.0, 0.0
                return (
                    float(min(values)),
                    float(max(values)),
                    float(np.mean(values)),
                    float(np.std(values)) if len(values) > 1 else 0.0,
                )

            ndvi_min, ndvi_max, ndvi_mean, ndvi_std = compute_stats(ndvi_values)
            endvi_min, endvi_max, endvi_mean, endvi_std = compute_stats(endvi_values)
            red_edge_min, red_edge_max, red_edge_mean, red_edge_std = compute_stats(red_edge_values)

            return InferenceVector(
                ndvi_min=ndvi_min,
                ndvi_max=ndvi_max,
                ndvi_mean=ndvi_mean,
                ndvi_std=ndvi_std,
                endvi_min=endvi_min,
                endvi_max=endvi_max,
                endvi_mean=endvi_mean,
                endvi_std=endvi_std,
                red_edge_min=red_edge_min,
                red_edge_max=red_edge_max,
                red_edge_mean=red_edge_mean,
                red_edge_std=red_edge_std,
            )

    @staticmethod
    async def generate_candidates(roi_id: UUID) -> list[CandidateLocation]:
        """Generate a deterministic grid of candidate locations for inference.

        Uses a regular 0.0045° (~500 m at equator) grid anchored on the ROI
        bounding-box origin and filtered by ST_Intersects against the ROI polygon.
        The list is sorted by (grid_row, grid_col) index for full reproducibility.

        Args:
            roi_id: The ROI ID.

        Returns:
            List of CandidateLocation objects inside the ROI.
        """
        async with async_session_factory() as session:
            # Get ROI bounding box
            bbox_query = select(
                func.ST_XMin(RegionOfInterest.geom).label("min_x"),
                func.ST_YMin(RegionOfInterest.geom).label("min_y"),
                func.ST_XMax(RegionOfInterest.geom).label("max_x"),
                func.ST_YMax(RegionOfInterest.geom).label("max_y"),
                RegionOfInterest.geom.label("roi_geom"),
            ).where(RegionOfInterest.id == roi_id)

            bbox_result = await session.execute(bbox_query)
            row = bbox_result.fetchone()

            if not row:
                return []

            min_x, min_y, max_x, max_y = row.min_x, row.min_y, row.max_x, row.max_y
            roi_geom = row.roi_geom

            # Regular grid anchored on bounding-box origin
            spacing = 0.0045  # ≈ 500 m at equator
            x_coords = np.arange(min_x, max_x + spacing, spacing)
            y_coords = np.arange(min_y, max_y + spacing, spacing)

            candidates: list[CandidateLocation] = []
            for gi, gx in enumerate(x_coords):
                for gj, gy in enumerate(y_coords):
                    point_wkt = f"SRID=4326;POINT({gx:.8f} {gy:.8f})"
                    # Filter by ST_Intersects so only points inside the ROI polygon are kept
                    intersects_query = select(
                        func.ST_Intersects(
                            func.ST_GeomFromEWKT(point_wkt),
                            roi_geom,
                        ).label("within")
                    )
                    intersects_result = await session.execute(intersects_query)
                    within = intersects_result.scalar()
                    if within:
                        candidates.append(
                            CandidateLocation(
                                roi_id=roi_id,
                                geom=f"POINT({gx:.8f} {gy:.8f})",
                                grid_row=gi,
                                grid_col=gj,
                            )
                        )

            # Sort by grid index for deterministic ordering
            candidates.sort(key=lambda c: (c.grid_row, c.grid_col))
            return candidates


async def build_feature_vector(
    ndvi: float | None,
    endvi: float | None,
    red_edge: float | None,
    lon: float,
    lat: float,
) -> np.ndarray:
    """Assemble the legacy [ndvi, endvi, red_edge, elevation] Stage 2 vector.

    This compatibility function is retained for the Wave 3 pipeline code path.
    New Stage 2 focal-classifier training/inference uses the 12-element aggregate
    vectors from ``FeatureExtractor`` methods.
    """
    elevation = await get_elevation(lon, lat)

    feature = np.array(
        [
            ndvi if ndvi is not None else 0.0,
            endvi if endvi is not None else 0.0,
            red_edge if red_edge is not None else 0.0,
            elevation,
        ],
        dtype=np.float32,
    ).reshape(1, 4)

    logger.debug(
        "feature_vector lon=%.6f lat=%.6f ndvi=%.4f endvi=%.4f red_edge=%.4f elevation=%.2f",
        lon,
        lat,
        float(feature[0, 0]),
        float(feature[0, 1]),
        float(feature[0, 2]),
        float(feature[0, 3]),
    )
    return feature


def retry_with_backoff(func: Any, max_retries: int = 3, base_delay: float = 1.0) -> Any:
    """Retry a callable with exponential backoff and jitter (T011).

    Args:
        func: Zero-argument callable to invoke.
        max_retries: Maximum retries before giving up (default 3).
        base_delay: Base delay in seconds (doubles each attempt plus jitter).

    Returns:
        Return value of ``func``, or ``None`` if all attempts are exhausted.
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as exc:
            if attempt >= max_retries:
                logger.warning(
                    "retry_with_backoff: exhausted %d retries — last error: %s",
                    max_retries,
                    exc,
                )
                return None
            delay = base_delay * (2**attempt) + random.uniform(0.0, 1.0)
            logger.warning(
                "retry_with_backoff: attempt %d/%d failed (%s), retrying in %.2fs",
                attempt + 1,
                max_retries,
                exc,
                delay,
            )
            time.sleep(delay)
    return None
