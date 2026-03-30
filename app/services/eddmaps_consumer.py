"""EDDMapS ingestion service with retry-safe behavior."""

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

EDDMAPS_OBSERVATIONS_URL = "https://www.eddmaps.org/api/observations"
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


async def _request_with_retry(
    client: httpx.AsyncClient,
    params: dict[str, Any],
    sleep: Any,
    jitter_fn: Any = random.random,
) -> tuple[list[dict[str, Any]] | None, int]:
    retries = 0
    total_sleep_budget = 0.0

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.get(EDDMAPS_OBSERVATIONS_URL, params=params)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("EDDMapS request failed: %s", exc)
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
                    "EDDMapS retry budget exceeded retries=%s budget_seconds=%.2f",
                    retries,
                    MAX_RETRY_BUDGET_SECONDS,
                )
                return None, retries
            await sleep(delay)
            total_sleep_budget += delay
            continue

        if response.status_code >= 400:
            logger.warning("EDDMapS returned non-retriable status=%s", response.status_code)
            return None, retries

        payload = response.json()
        if isinstance(payload, dict):
            records = payload.get("results") or payload.get("data") or []
        elif isinstance(payload, list):
            records = payload
        else:
            records = []
        return records, retries

    logger.warning("EDDMapS request exhausted retry budget")
    return None, retries


async def sync_eddmaps(
    session: AsyncSession,
    bbox: tuple[float, float, float, float],
    taxon_ids: list[int] | None = None,
    sync_run_id: str | None = None,
    client: httpx.AsyncClient | None = None,
    sleep: Any = asyncio.sleep,
) -> SyncStats:
    """Sync EDDMapS observations and persist canonical records."""
    minx, miny, maxx, maxy = bbox
    params: dict[str, Any] = {
        "bbox": f"{minx},{miny},{maxx},{maxy}",
    }
    if taxon_ids:
        params["taxon_id"] = ",".join(str(item) for item in taxon_ids)

    stats = SyncStats(source="EDDMapS")

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)

    try:
        records, retries = await _request_with_retry(client, params=params, sleep=sleep)
        stats.retries += retries

        if records is None:
            stats.failures += 1
            return stats

        for item in records:
            external_id = item.get("id") or item.get("external_id")
            lat = item.get("latitude")
            lon = item.get("longitude")
            if external_id is None or lat is None or lon is None:
                logger.info(
                    "sync_skip source=EDDMapS sync_run_id=%s reason=missing_identity_or_geometry",
                    sync_run_id,
                )
                stats.records_skipped += 1
                continue

            insert_stmt = (
                insert(GroundTruthObservation)
                .values(
                    source="EDDMapS",
                    external_id=str(external_id),
                    species_label=item.get("species_label") or item.get("species") or "unknown",
                    observer=item.get("observer"),
                    observed_at=_parse_observed_date(item.get("observed_at") or item.get("date")),
                    geom=from_shape(Point(float(lon), float(lat)), srid=4326),
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
                    "sync_skip source=EDDMapS sync_run_id=%s reason=duplicate external_id=%s",
                    sync_run_id,
                    external_id,
                )
                stats.records_skipped += 1
            else:
                stats.records_inserted += 1

        await session.commit()
        return stats
    except asyncio.CancelledError:
        logger.warning("EDDMapS sync cancelled sync_run_id=%s", sync_run_id)
        await session.rollback()
        raise
    finally:
        if owns_client:
            await client.aclose()
