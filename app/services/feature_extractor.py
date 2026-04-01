"""Stage 2 feature vector assembly: spectral indices + resilient USGS 3DEP elevation."""

from __future__ import annotations

import logging

import numpy as np

from app.services.usgs_3dep_client import get_elevation

logger = logging.getLogger(__name__)


async def build_feature_vector(
    ndvi: float | None,
    endvi: float | None,
    red_edge: float | None,
    lon: float,
    lat: float,
) -> np.ndarray:
    """Assemble the [ndvi, endvi, red_edge, elevation] feature vector for Stage 2.

    Elevation is fetched from USGS 3DEP; falls back to 0.0 on any failure.
    None spectral values are substituted with 0.0.

    Args:
        ndvi: NDVI value from spectral_time_series (may be None).
        endvi: ENDVI value from spectral_time_series (may be None).
        red_edge: Red-edge value from spectral_time_series (may be None).
        lon: Longitude (WGS84) for elevation lookup.
        lat: Latitude (WGS84) for elevation lookup.

    Returns:
        numpy array of shape (1, 4) — [ndvi, endvi, red_edge, elevation].
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
