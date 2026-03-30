"""Spectral index helpers for Sentinel-2 windowed band reads."""

from __future__ import annotations

import logging

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.errors import RasterioError
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

logger = logging.getLogger(__name__)

EPSILON = 1e-10


def _finite_mean(array: np.ndarray) -> float | None:
    finite = np.isfinite(array)
    if not np.any(finite):
        return None
    return float(np.nanmean(array))


def read_band_window(
    href: str,
    roi_bounds_4326: tuple[float, float, float, float],
) -> np.ndarray | None:
    """Read one raster band using a bounds window transformed into the scene CRS."""
    try:
        with (
            rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
            ),
            rasterio.open(href) as src,
        ):
            scene_bounds = transform_bounds(CRS.from_epsg(4326), src.crs, *roi_bounds_4326)
            window = from_bounds(*scene_bounds, transform=src.transform)
            band = src.read(1, window=window, boundless=True, masked=True)
            array = np.asarray(band.filled(np.nan), dtype=np.float32)
            if array.size == 0:
                return None
            return array
    except RasterioError as exc:
        logger.warning("band_read_failed href=%s error=%s", href, exc)
        return None


def compute_ndvi(b08: np.ndarray, b04: np.ndarray) -> float | None:
    """Compute spatial-mean NDVI clamped to [-1, 1]."""
    ndvi = (b08 - b04) / (b08 + b04 + EPSILON)
    mean_value = _finite_mean(ndvi)
    if mean_value is None:
        return None
    return float(np.clip(mean_value, -1.0, 1.0))


def compute_endvi(b08: np.ndarray, b03: np.ndarray, b04: np.ndarray) -> float | None:
    """Compute spatial-mean ENDVI clamped to [-1, 1]."""
    endvi = (b08 + b03 - (2.0 * b04)) / (b08 + b03 + (2.0 * b04) + EPSILON)
    mean_value = _finite_mean(endvi)
    if mean_value is None:
        return None
    return float(np.clip(mean_value, -1.0, 1.0))


def compute_red_edge(b8a: np.ndarray, b05: np.ndarray) -> float | None:
    """Compute spatial-mean CIre red-edge index clamped to [-1, 20]."""
    red_edge = (b8a / (b05 + EPSILON)) - 1.0
    mean_value = _finite_mean(red_edge)
    if mean_value is None:
        return None
    return float(np.clip(mean_value, -1.0, 20.0))
