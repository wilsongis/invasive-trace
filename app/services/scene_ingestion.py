"""Scene ingestion orchestration from STAC discovery to spectral upsert."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2.shape import to_shape
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.roi import RegionOfInterest
from app.models.spectral import SpectralTimeSeries
from app.schemas.spectral import SceneDateRange, SceneIngestResponse
from app.services import cloud_mask, indices, stac_client
from app.services.tiling import Tile, compute_tiles_for_roi

logger = logging.getLogger(__name__)

REQUIRED_BAND_KEYS = ("B03", "B04", "B05", "B08", "B8A")
SCL_BAND_KEY = "SCL"


@dataclass(slots=True)
class IngestionStats:
    """Mutable counters for one ingestion run."""

    scenes_queried: int = 0
    scenes_inserted: int = 0
    scenes_updated: int = 0
    scenes_masked: int = 0
    scenes_skipped: int = 0


async def _process_item_for_bounds(
    item,
    bounds_wkt: str,
    bounds: tuple[float, float, float, float],
    roi_id: UUID,
    platform: str,
    session: AsyncSession,
    stats: IngestionStats,
) -> None:
    """Process a single STAC item for a given bounds (ROI or tile)."""
    try:
        assets = item.assets or {}
        missing = [band for band in REQUIRED_BAND_KEYS if band not in assets]
        if missing:
            logger.warning(
                "scene_skip_missing_assets stac_item=%s missing=%s",
                item.id,
                missing,
            )
            stats.scenes_skipped += 1
            return

        scl_asset = assets.get(SCL_BAND_KEY)
        cloud_cover, is_masked = cloud_mask.compute_cloud_fraction(
            scl_asset.href if scl_asset else None,
            bounds,
        )
        ndvi: float | None = None
        endvi: float | None = None
        red_edge: float | None = None

        if is_masked:
            stats.scenes_masked += 1
        else:
            b03 = indices.read_band_window(assets["B03"].href, bounds)
            b04 = indices.read_band_window(assets["B04"].href, bounds)
            b05 = indices.read_band_window(assets["B05"].href, bounds)
            b08 = indices.read_band_window(assets["B08"].href, bounds)
            b8a = indices.read_band_window(assets["B8A"].href, bounds)

            if any(band is None for band in (b03, b04, b05, b08, b8a)):
                logger.warning("scene_skip_band_read stac_item=%s", item.id)
                stats.scenes_skipped += 1
                return

            assert b03 is not None and b04 is not None and b05 is not None
            assert b08 is not None and b8a is not None
            ndvi = indices.compute_ndvi(b08, b04)
            endvi = indices.compute_endvi(b08, b03, b04)
            red_edge = indices.compute_red_edge(b8a, b05)

        scene_datetime = item.datetime or date.fromisoformat(item.properties["datetime"][:10])
        # Handle both datetime (has .date() method) and date objects
        from datetime import datetime as dt_type

        if isinstance(scene_datetime, dt_type):
            scene_date = scene_datetime.date()
        else:
            scene_date = scene_datetime

        row_data = {
            "roi_id": roi_id,
            "scene_date": scene_date,
            "platform": platform,
            "stac_item": item.id,
            "ndvi": ndvi,
            "endvi": endvi,
            "red_edge": red_edge,
            "cloud_cover": cloud_cover,
            "is_masked": is_masked,
        }

        stmt = insert(SpectralTimeSeries).values(**row_data)
        update_cols = [
            "scene_date",
            "platform",
            "ndvi",
            "endvi",
            "red_edge",
            "cloud_cover",
            "is_masked",
        ]
        upsert_stmt = stmt.on_conflict_do_update(
            constraint="uq_spectral_roi_item",
            set_={col: getattr(stmt.excluded, col) for col in update_cols},
        ).returning(text("xmax = 0 AS inserted"))

        inserted = bool((await session.execute(upsert_stmt)).scalar_one())
        if inserted:
            stats.scenes_inserted += 1
        else:
            stats.scenes_updated += 1
    except Exception as exc:  # pragma: no cover - defensive continuation path
        logger.warning(
            "scene_skip_error stac_item=%s error=%s",
            getattr(item, "id", "unknown"),
            exc,
        )
        stats.scenes_skipped += 1


async def run_ingestion(
    roi_id: UUID,
    start_date: date,
    end_date: date,
    platform: str,
    session: AsyncSession,
    tile_size: int | None = None,
) -> SceneIngestResponse:
    """Ingest Sentinel-2 scenes for one ROI and persist spectral aggregates.

    Args:
        roi_id: The ROI to ingest scenes for.
        start_date: Start date for scene query.
        end_date: End date for scene query.
        platform: Platform name (must be 'sentinel-2').
        session: Database session.
        tile_size: Optional tile size override for tiled processing.
    """
    if platform != "sentinel-2":
        raise ValueError("platform must be 'sentinel-2' for Wave 005")

    roi = await session.get(RegionOfInterest, roi_id)
    if roi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROI {roi_id} not found",
        )

    roi_shape = to_shape(roi.geom)
    roi_bounds = roi_shape.bounds

    # Compute tiles for parallel processing
    tiles = compute_tiles_for_roi(roi, tile_size)

    if not tiles:
        # Fall back to whole ROI processing if tiling fails
        logger.warning("tiling_failed_fallback_to_whole_roi roi_id=%s", roi_id)
        tiles = [Tile(tile_id=0, geometry_wkt=roi_shape.wkt, bounds=roi_bounds, width=0, height=0)]

    stats = IngestionStats()

    for tile in tiles:
        tile_bounds = tile.bounds
        tile_bounds_wkt = tile.geometry_wkt

        # Query scenes for this tile
        items = await stac_client.query_scenes(
            roi_geom_wkt=tile_bounds_wkt,
            start_date=start_date,
            end_date=end_date,
            platform=platform,
        )

        stats.scenes_queried += len(items)

        for item in items:
            await _process_item_for_bounds(
                item, tile_bounds_wkt, tile_bounds, roi_id, platform, session, stats
            )

    await session.commit()

    return SceneIngestResponse(
        roi_id=roi_id,
        scenes_queried=stats.scenes_queried,
        scenes_inserted=stats.scenes_inserted,
        scenes_updated=stats.scenes_updated,
        scenes_masked=stats.scenes_masked,
        scenes_skipped=stats.scenes_skipped,
        date_range=SceneDateRange(start=start_date, end=end_date),
    )
