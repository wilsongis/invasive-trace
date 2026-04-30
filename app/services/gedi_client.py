"""GEDI (Global Ecosystem Dynamics Investigation) data client.

Provides authentication and data‑fetching utilities for NASA Earthdata
GEDI Level‑2A HDF5 products.  Authentication uses the standard Earthdata
username/password stored in environment variables ``EARTHDATA_USER`` and
``EARTHDATA_PASSWORD``.

Supported products
------------------
- GEDI02_A (Level‑2A): canopy height, quality flag, footprint coordinates
- GEDI02_B (Level‑2B): plant area index, cover (future extension)

Usage example
-------------
>>> client = GEDIClient()
>>> records = await client.fetch_footprints(roi_geom, date_range=("2023-01-01", "2023-12-31"))
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Earthdata API constants (public, no secrets)
# ---------------------------------------------------------------------------
EARTHDATA_BASE_URL = "https://cmr.earthdata.nasa.gov/search"
GEDI_PROVIDER = "LPDAAC_ECS"
GEDI_SHORT_NAME_L2A = "GEDI02_A"
GEDI_SHORT_NAME_L2B = "GEDI02_B"

# Quality flag value meaning "high quality" in Level‑2A
QUALITY_FLAG_HIGH = 1


@dataclass
class GEDIFootprint:
    """A single GEDI lidar footprint record.

    Attributes
    ----------
    footprint_id:
        Unique shot number from the HDF5 file (``shot_number`` dataset).
    acquisition_date:
        UTC date of the acquisition.
    latitude:
        WGS‑84 latitude (degrees).
    longitude:
        WGS‑84 longitude (degrees).
    canopy_height:
        Relative height at 98th percentile (``rh98``), in metres.
    biomass:
        Above‑ground biomass density estimate (Mg/ha), ``None`` if not
        available for this product version.
    quality_flag:
        Quality flag integer from the HDF5 file (1 = high quality).
    """

    footprint_id: str
    acquisition_date: date
    latitude: float
    longitude: float
    canopy_height: float
    biomass: float | None = None
    quality_flag: int = 0


@dataclass
class GEDIClientConfig:
    """Runtime configuration for ``GEDIClient``.

    Values default to environment variables so they can be overridden in
    tests without touching the process environment.
    """

    earthdata_user: str = field(
        default_factory=lambda: os.environ.get("EARTHDATA_USER", "")
    )
    earthdata_password: str = field(
        default_factory=lambda: os.environ.get("EARTHDATA_PASSWORD", "")
    )
    max_retries: int = 3
    backoff_factor: float = 1.5


class GEDIClient:
    """Async client for fetching GEDI Level‑2A footprint data.

    This is a **stub implementation**.  The full implementation should:

    1. Authenticate against NASA Earthdata using the ``requests`` or
       ``httpx`` library with Basic Auth.
    2. Query the CMR (Common Metadata Repository) for granules that
       spatially intersect the ROI polygon.
    3. Download each granule's HDF5 file and parse it with ``h5py``.
    4. Yield ``GEDIFootprint`` records filtered by ``quality_flag == 1``.

    All network calls must implement exponential back‑off with a maximum of
    ``config.max_retries`` retries to align with the project's API failure
    mode policy (Section 5 of AGENTS.md).
    """

    def __init__(self, config: GEDIClientConfig | None = None) -> None:
        self.config = config or GEDIClientConfig()
        if not self.config.earthdata_user:
            logger.warning(
                "EARTHDATA_USER is not set — GEDI client will not be able to "
                "authenticate.  Set the environment variable before calling "
                "fetch_footprints()."
            )

    async def fetch_footprints(
        self,
        roi_wkt: str,
        date_from: str,
        date_to: str,
        product: str = GEDI_SHORT_NAME_L2A,
    ) -> AsyncIterator[GEDIFootprint]:
        """Async generator yielding GEDI footprints within an ROI.

        Parameters
        ----------
        roi_wkt:
            Well‑Known Text representation of the ROI polygon (WGS‑84).
        date_from:
            Start date, ISO 8601 (``YYYY-MM-DD``).
        date_to:
            End date, ISO 8601 (``YYYY-MM-DD``).
        product:
            GEDI product short name (default: ``GEDI02_A``).

        Raises
        ------
        NotImplementedError
            Always, until a concrete implementation is provided.  Callers
            should catch this and log a skip, consistent with the AlphaEarth
            failure‑mode policy.
        """
        raise NotImplementedError(
            "GEDIClient.fetch_footprints() is not yet implemented.  "
            "Install h5py and httpx, then implement CMR granule search and "
            "HDF5 parsing."
        )
        # Satisfy the type checker — unreachable but required for async generator
        yield GEDIFootprint(  # type: ignore[misc]  # pragma: no cover
            footprint_id="",
            acquisition_date=date.today(),
            latitude=0.0,
            longitude=0.0,
            canopy_height=0.0,
        )