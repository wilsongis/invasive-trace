"""USGS 3DEP elevation point query with exponential backoff and 0.0 fallback."""

from __future__ import annotations

import asyncio
import logging
import random

import httpx

logger = logging.getLogger(__name__)

# Public endpoint — no auth required (AGENTS.md Section 5)
USGS_3DEP_BASE_URL = "https://epqs.nationalmap.gov/v1/json"

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
RETRY_EXPONENTIAL_FACTOR = 2.0
RETRY_JITTER_RATIO = 0.1
ELEVATION_FALLBACK = 0.0


async def get_elevation(lon: float, lat: float) -> float:
    """Retrieve point elevation from the USGS 3DEP service.

    Applies exponential backoff on HTTP 429 (max 3 retries).
    On any unrecoverable failure, logs a warning and returns 0.0.
    Never raises an unhandled exception (FR-013, NFR-005).

    Args:
        lon: Longitude in WGS84.
        lat: Latitude in WGS84.

    Returns:
        Elevation in metres, or 0.0 on failure.
    """
    params = {"x": lon, "y": lat, "units": "Meters", "output": "json"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.get(USGS_3DEP_BASE_URL, params=params)

                if response.status_code == 429:
                    if attempt < MAX_RETRIES:
                        delay = _backoff_delay(attempt)
                        logger.warning(
                            "usgs_3dep_rate_limited lon=%.6f lat=%.6f attempt=%d retry_in=%.2fs",
                            lon,
                            lat,
                            attempt + 1,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.warning(
                        "usgs_3dep_max_retries_exceeded lon=%.6f lat=%.6f fallback=%.1f",
                        lon,
                        lat,
                        ELEVATION_FALLBACK,
                    )
                    return ELEVATION_FALLBACK

                response.raise_for_status()
                data = response.json()
                elevation = float(data.get("value", ELEVATION_FALLBACK))
                return elevation

            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "usgs_3dep_http_error lon=%.6f lat=%.6f status=%d fallback=%.1f",
                    lon,
                    lat,
                    exc.response.status_code,
                    ELEVATION_FALLBACK,
                )
                return ELEVATION_FALLBACK
            except Exception as exc:
                logger.warning(
                    "usgs_3dep_request_error lon=%.6f lat=%.6f error=%s fallback=%.1f",
                    lon,
                    lat,
                    exc,
                    ELEVATION_FALLBACK,
                )
                return ELEVATION_FALLBACK

    return ELEVATION_FALLBACK  # pragma: no cover


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter."""
    base = RETRY_BASE_DELAY * (RETRY_EXPONENTIAL_FACTOR**attempt)
    jitter = base * RETRY_JITTER_RATIO * random.random()
    return base + jitter
