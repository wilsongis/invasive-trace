"""Spatial tiling utility for parallel raster processing.

Splits a region of interest into configurable tiles, enabling independent
processing of each tile during scene ingestion and ML inference.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from geoalchemy2.shape import to_shape
from shapely.geometry import box

from app.config import get_settings
from app.models.roi import RegionOfInterest

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Tile:
    """A single spatial tile with its bounding box."""

    tile_id: int
    geometry_wkt: str
    bounds: tuple[float, float, float, float]  # (minx, miny, maxx, maxy)
    width: float
    height: float


def compute_tiles_for_roi(
    roi: RegionOfInterest,
    tile_size: int | None = None,
) -> list[Tile]:
    """Split an ROI polygon into tiles of the configured size.

    Args:
        roi: The region of interest to tile.
        tile_size: Optional override for tile size in meters (defaults to TILE_SIZE config).

    Returns:
        List of Tile objects covering the ROI.
    """
    settings = get_settings()
    size = tile_size if tile_size is not None else settings.TILE_SIZE

    roi_shape = to_shape(roi.geom)
    if roi_shape is None:
        logger.warning("roi_has_no_geometry roi_id=%s", roi.id)
        return []

    # Project to a metric CRS for accurate tiling (UTM zone based on centroid)
    centroid = roi_shape.centroid
    utm_zone = int((centroid.x + 180) // 6 + 1)
    epsg = 32600 + utm_zone if centroid.y >= 0 else 32700 + utm_zone
    metric_crs = f"EPSG:{epsg}"

    import pyproj
    from shapely.ops import transform

    project_to_metric = pyproj.Transformer.from_crs(
        "EPSG:4326", metric_crs, always_xy=True
    ).transform
    project_to_wgs84 = pyproj.Transformer.from_crs(
        metric_crs, "EPSG:4326", always_xy=True
    ).transform

    roi_metric = transform(project_to_metric, roi_shape)
    bounds = roi_metric.bounds  # (minx, miny, maxx, maxy)

    tiles: list[Tile] = []
    tile_id = 0

    minx, miny, maxx, maxy = bounds
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            tile_box = box(x, y, min(x + size, maxx), min(y + size, maxy))
            # Intersect with ROI to get valid area
            tile_geom = tile_box.intersection(roi_metric)
            if not tile_geom.is_empty and tile_geom.area > 0:
                # Transform back to WGS84 for storage/query
                tile_wgs84 = transform(project_to_wgs84, tile_geom)
                tile_bounds = tile_wgs84.bounds
                tiles.append(
                    Tile(
                        tile_id=tile_id,
                        geometry_wkt=tile_wgs84.wkt,
                        bounds=tile_bounds,
                        width=tile_box.bounds[2] - tile_box.bounds[0],
                        height=tile_box.bounds[3] - tile_box.bounds[1],
                    )
                )
                tile_id += 1
            y += size
        x += size

    logger.info(
        "tiles_computed roi_id=%s tile_count=%d tile_size=%d",
        roi.id,
        len(tiles),
        size,
    )
    return tiles


def get_tile_bounds_wkt(tile: Tile) -> str:
    """Get the WKT representation of a tile's bounding box for STAC queries.

    Args:
        tile: The tile to get bounds for.

    Returns:
        WKT string of the tile's bounding box polygon.
    """
    minx, miny, maxx, maxy = tile.bounds
    return box(minx, miny, maxx, maxy).wkt
