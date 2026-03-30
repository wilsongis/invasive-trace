"""QA60 cloud masking utilities for Sentinel-2 scenes."""

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


def compute_cloud_fraction_from_array(qa60_array: np.ndarray) -> tuple[float, bool]:
    """Compute cloud fraction using QA60 bits 10/11 from a uint16 array."""
    if qa60_array.size == 0:
        return 1.0, True

    qa60 = qa60_array.astype(np.uint16, copy=False)
    cloud_pixels = (((qa60 >> 10) & 0b1) | ((qa60 >> 11) & 0b1)) > 0
    cloud_fraction = float(np.count_nonzero(cloud_pixels) / cloud_pixels.size)
    return cloud_fraction, cloud_fraction > CLOUD_MASK_THRESHOLD


def compute_cloud_fraction(
    qa60_href: str | None,
    roi_bounds_4326: tuple[float, float, float, float],
) -> tuple[float, bool]:
    """Read QA60 over an ROI window and return cloud fraction plus mask decision."""
    if not qa60_href:
        logger.warning("qa60_missing defaulting_to_masked")
        return 1.0, True

    try:
        with (
            rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
            ),
            rasterio.open(qa60_href) as src,
        ):
            scene_bounds = transform_bounds(CRS.from_epsg(4326), src.crs, *roi_bounds_4326)
            window = from_bounds(*scene_bounds, transform=src.transform)
            qa60 = src.read(1, window=window, boundless=True, masked=True)
            data = np.asarray(qa60.filled(0), dtype=np.uint16)
            return compute_cloud_fraction_from_array(data)
    except RasterioError as exc:
        logger.warning("qa60_read_failed href=%s error=%s", qa60_href, exc)
        return 1.0, True
