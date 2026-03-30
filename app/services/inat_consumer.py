"""iNaturalist ingestion service with retry-safe behavior."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation import GroundTruthObservation

logger = logging.getLogger(__name__)

INAT_OBSERVATIONS_URL = "https://api.inaturalist.org/v1/observations"
REQUEST_TIMEOUT_SECONDS = 20.0
RETRY_BASE_DELAY_SECONDS = 0.25
RETRY_EXPONENTIAL_FACTOR = 2.0
MAX_RETRIES = 3
RETRY_JITTER_POLICY = "proportional"
RETRY_JITTER_RATIO = 0.10
MAX_RETRY_BUDGET_SECONDS = 1.75


@dataclass(slots=True)
class SyncStats:
    """Per-source sync accounting data."""

    source: str
    records_inserted: int = 0
    records_skipped: int = 0
    retries: int = 0
    failures: int = 0


def _parse_observed_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _extract_point(payload: dict[str, Any]) -> Point | None:
    geojson = payload.get("geojson") or {}
    coords = geojson.get("coordinates")
    if isinstance(coords, list) and len(coords) == 2:
        lon, lat = coords
        return Point(float(lon), float(lat))

    location = payload.get("location")
    if isinstance(location, str) and "," in location:
        lat_str, lon_str = location.split(",", maxsplit=1)
        return Point(float(lon_str.strip()), float(lat_str.strip()))

    return None


async def _request_with_retry(
    client: httpx.AsyncClient,
    params: dict[str, Any],
    sleep: Any,
    jitter_fn: Any = random.random,
) -> tuple[dict[str, Any] | None, int]:
    retries = 0
    total_sleep_budget = 0.0

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.get(INAT_OBSERVATIONS_URL, params=params)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("iNaturalist request failed: %s", exc)
            return None, retries

        if response.status_code == httpx.codes.TOO_MANY_REQUESTS and attempt < MAX_RETRIES:
            retries += 1
            base_delay = RETRY_BASE_DELAY_SECONDS * (RETRY_EXPONENTIAL_FACTOR**attempt)
            jitter = 0.0
            if RETRY_JITTER_POLICY == "proportional":
                jitter = base_delay * RETRY_JITTER_RATIO * float(jitter_fn())
            delay = base_delay + jitter
            if total_sleep_budget + delay > MAX_RETRY_BUDGET_SECONDS:
                logger.warning(
                    "iNaturalist retry budget exceeded retries=%s budget_seconds=%.2f",
                    retries,
                    MAX_RETRY_BUDGET_SECONDS,
                )
                return None, retries
            await sleep(delay)
            total_sleep_budget += delay
            continue

        if response.status_code >= 400:
            logger.warning("iNaturalist returned non-retriable status=%s", response.status_code)
            return None, retries

        return response.json(), retries

    logger.warning("iNaturalist request exhausted retry budget")
    return None, retries


async def sync_inaturalist(
    session: AsyncSession,
    bbox: tuple[float, float, float, float],
    taxon_ids: list[int] | None = None,
    sync_run_id: str | None = None,
    client: httpx.AsyncClient | None = None,
    sleep: Any = asyncio.sleep,
) -> SyncStats:
    """Sync iNaturalist observations and persist canonical records."""
    minx, miny, maxx, maxy = bbox
    params: dict[str, Any] = {
        "swlat": miny,
        "swlng": minx,
        "nelat": maxy,
        "nelng": maxx,
        "per_page": 200,
        "order": "desc",
        "order_by": "observed_on",
    }
    if taxon_ids:
        params["taxon_id"] = ",".join(str(item) for item in taxon_ids)

    stats = SyncStats(source="iNaturalist")

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)

    try:
        payload, retries = await _request_with_retry(client, params=params, sleep=sleep)
        stats.retries += retries

        if payload is None:
            stats.failures += 1
            return stats

        for item in payload.get("results", []):
            external_id = item.get("id")
            point = _extract_point(item)
            if external_id is None or point is None:
                logger.info(
                    "sync_skip source=iNaturalist sync_run_id=%s "
                    "reason=missing_identity_or_geometry",
                    sync_run_id,
                )
                stats.records_skipped += 1
                continue

            insert_stmt = (
                insert(GroundTruthObservation)
                .values(
                    source="iNaturalist",
                    external_id=str(external_id),
                    species_label=((item.get("taxon") or {}).get("name") or "unknown"),
                    observer=(item.get("user") or {}).get("login"),
                    observed_at=_parse_observed_date(item.get("observed_on")),
                    geom=from_shape(point, srid=4326),
                    is_confirmed=True,
                    raw_payload=item,
                )
                .on_conflict_do_nothing(
                    index_elements=["source", "external_id"],
                    index_where=GroundTruthObservation.external_id.is_not(None),
                )
                .returning(GroundTruthObservation.id)
            )
            result = await session.execute(insert_stmt)
            inserted_id = result.scalar_one_or_none()
            if inserted_id is None:
                logger.info(
                    "sync_skip source=iNaturalist sync_run_id=%s reason=duplicate external_id=%s",
                    sync_run_id,
                    external_id,
                )
                stats.records_skipped += 1
            else:
                stats.records_inserted += 1

        await session.commit()
        return stats
    except asyncio.CancelledError:
        logger.warning("iNaturalist sync cancelled sync_run_id=%s", sync_run_id)
        await session.rollback()
        raise
    finally:
        if owns_client:
            await client.aclose()
