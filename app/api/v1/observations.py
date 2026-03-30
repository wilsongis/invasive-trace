"""Observation sync endpoints."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import to_shape
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.roi import RegionOfInterest
from app.services.eddmaps_consumer import SyncStats as EddmapsSyncStats
from app.services.eddmaps_consumer import sync_eddmaps
from app.services.inat_consumer import SyncStats as InatSyncStats
from app.services.inat_consumer import sync_inaturalist

router = APIRouter(prefix="/observations", tags=["observations"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
logger = logging.getLogger(__name__)
SOURCE_TIMEOUT_SECONDS = 30.0


class ObservationSyncRequest(BaseModel):
    """ROI-scoped sync request payload."""

    roi_id: UUID
    taxon_ids: list[int] = Field(default_factory=list)


class ObservationSyncResponse(BaseModel):
    """Summary response for observation sync jobs."""

    sync_run_id: str
    sources_polled: list[str]
    records_inserted: int
    records_skipped: int
    source_stats: dict


@router.post("/sync", response_model=ObservationSyncResponse)
async def sync_observations(
    payload: ObservationSyncRequest,
    db: DbSession,
) -> ObservationSyncResponse:
    """Run iNaturalist and EDDMapS synchronization for a given ROI."""
    roi = await db.get(RegionOfInterest, payload.roi_id)
    if roi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROI_NOT_FOUND", "message": "ROI not found"},
        )

    sync_run_id = str(uuid.uuid4())
    minx, miny, maxx, maxy = to_shape(roi.geom).bounds

    try:
        inat_stats = await asyncio.wait_for(
            sync_inaturalist(
                session=db,
                bbox=(minx, miny, maxx, maxy),
                taxon_ids=payload.taxon_ids,
                sync_run_id=sync_run_id,
            ),
            timeout=SOURCE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "sync_timeout sync_run_id=%s roi_id=%s source=iNaturalist",
            sync_run_id,
            payload.roi_id,
        )
        inat_stats = InatSyncStats(source="iNaturalist", failures=1)

    try:
        eddmaps_stats = await asyncio.wait_for(
            sync_eddmaps(
                session=db,
                bbox=(minx, miny, maxx, maxy),
                taxon_ids=payload.taxon_ids,
                sync_run_id=sync_run_id,
            ),
            timeout=SOURCE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "sync_timeout sync_run_id=%s roi_id=%s source=EDDMapS",
            sync_run_id,
            payload.roi_id,
        )
        eddmaps_stats = EddmapsSyncStats(source="EDDMapS", failures=1)

    for source_name, stats in (("iNaturalist", inat_stats), ("EDDMapS", eddmaps_stats)):
        failure_class = "none" if stats.failures == 0 else "source_failure"
        logger.info(
            "sync_audit sync_run_id=%s roi_id=%s source=%s retry_count=%s "
            "records_inserted=%s records_skipped=%s failure_class=%s",
            sync_run_id,
            payload.roi_id,
            source_name,
            stats.retries,
            stats.records_inserted,
            stats.records_skipped,
            failure_class,
        )

    return ObservationSyncResponse(
        sync_run_id=sync_run_id,
        sources_polled=["iNaturalist", "EDDMapS"],
        records_inserted=inat_stats.records_inserted + eddmaps_stats.records_inserted,
        records_skipped=inat_stats.records_skipped + eddmaps_stats.records_skipped,
        source_stats={
            "iNaturalist": asdict(inat_stats),
            "EDDMapS": asdict(eddmaps_stats),
        },
    )
