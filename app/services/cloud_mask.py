"""Cloud masking utilities for Sentinel-2 L2A scenes using SCL band."""

from __future__ import annotations

import logging

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.errors import RasterioError
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

logger = logging.getLogger(__name__)

CLOUD_MASK_THRESHOLD = 0.20

# SCL cloud classes per Sentinel-2 L2A product specification
# Class 8: cloud medium probability
# Class 9: cloud high probability
# Class 10: thin cirrus
# Class 11: snow/ice (treated as cloud for conservative masking)
SCL_CLOUD_CLASSES = {8, 9, 10, 11}


def compute_cloud_fraction_from_scl(scl_array: np.ndarray) -> tuple[float, bool]:
    """Compute cloud fraction using SCL classification band from Sentinel-2 L2A."""
    if scl_array.size == 0:
        return 1.0, True

    scl = scl_array.astype(np.uint8, copy=False)
    cloud_pixels = np.isin(scl, list(SCL_CLOUD_CLASSES))
    cloud_fraction = float(np.count_nonzero(cloud_pixels) / cloud_pixels.size)
    return cloud_fraction, cloud_fraction > CLOUD_MASK_THRESHOLD


def compute_cloud_fraction(
    scl_href: str | None,
    roi_bounds_4326: tuple[float, float, float, float],
) -> tuple[float, bool]:
    """Read SCL over an ROI window and return cloud fraction plus mask decision.

    Uses the Sentinel-2 L2A Scene Classification (SCL) band instead of QA60,
    which is only available for L1C items.
    """
    if not scl_href:
        logger.warning("scl_missing defaulting_to_masked")
        return 1.0, True

    try:
        with (
            rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
            ),
            rasterio.open(scl_href) as src,
        ):
            scene_bounds = transform_bounds(CRS.from_epsg(4326), src.crs, *roi_bounds_4326)
            window = from_bounds(*scene_bounds, transform=src.transform)
            scl = src.read(1, window=window, boundless=True, masked=True)
            data = np.asarray(scl.filled(0), dtype=np.uint8)
            return compute_cloud_fraction_from_scl(data)
    except RasterioError as exc:
        logger.warning("scl_read_failed href=%s error=%s", scl_href, exc)
        return 1.0, True
