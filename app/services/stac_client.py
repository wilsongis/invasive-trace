"""Planetary Computer STAC discovery helpers for Sentinel-2 ingestion."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import date

import planetary_computer
from pydantic import BaseModel
from pystac import Item
from pystac_client import Client
from shapely import wkt

from app.config import get_settings

logger = logging.getLogger(__name__)

PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SENTINEL2_COLLECTION = "sentinel-2-l2a"
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 0.25
RETRY_EXPONENTIAL_FACTOR = 2.0
RETRY_JITTER_RATIO = 0.10


class StacQueryUnavailableError(RuntimeError):
    """Raised when STAC discovery is unavailable after all retries."""


class SceneQuery(BaseModel):
    """Normalized STAC query arguments."""

    roi_geom_wkt: str
    start_date: date
    end_date: date
    platform: str = "sentinel-2"


def _is_rate_limited_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "too many requests" in message or "rate limit" in message


def _bbox_from_wkt(roi_geom_wkt: str) -> tuple[float, float, float, float]:
    geom = wkt.loads(roi_geom_wkt)
    minx, miny, maxx, maxy = geom.bounds
    return float(minx), float(miny), float(maxx), float(maxy)


def _query_once(query: SceneQuery) -> list[Item]:
    settings = get_settings()
    if settings.PC_SDK_SUBSCRIPTION_KEY:
        planetary_computer.settings.set_subscription_key(settings.PC_SDK_SUBSCRIPTION_KEY)

    bbox = _bbox_from_wkt(query.roi_geom_wkt)
    client = Client.open(PC_STAC_URL)
    search = client.search(
        collections=[SENTINEL2_COLLECTION],
        bbox=list(bbox),
        datetime=f"{query.start_date.isoformat()}/{query.end_date.isoformat()}",
        query={"eo:cloud_cover": {"lt": 80}},
    )

    signed_items: list[Item] = []
    for item in search.items():
        signed_items.append(planetary_computer.sign_inplace(item))
    return signed_items


async def query_scenes(
    roi_geom_wkt: str,
    start_date: date,
    end_date: date,
    platform: str = "sentinel-2",
) -> list[Item]:
    """Query and sign Sentinel-2 STAC items with 429 retry handling."""
    if platform != "sentinel-2":
        raise ValueError("platform must be 'sentinel-2' for Wave 005")

    query = SceneQuery(
        roi_geom_wkt=roi_geom_wkt,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            return await asyncio.to_thread(_query_once, query)
        except Exception as exc:  # pragma: no cover - external client error surface
            if attempt < MAX_RETRIES and _is_rate_limited_error(exc):
                base_delay = RETRY_BASE_DELAY_SECONDS * (RETRY_EXPONENTIAL_FACTOR**attempt)
                jitter = base_delay * RETRY_JITTER_RATIO * random.random()
                await asyncio.sleep(base_delay + jitter)
                continue
            logger.warning("stac_query_unavailable attempt=%s error=%s", attempt + 1, exc)
            raise StacQueryUnavailableError("Planetary Computer STAC query failed") from exc

    raise StacQueryUnavailableError("Planetary Computer STAC query exhausted retries")
