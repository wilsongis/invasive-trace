"""Unit tests for benchmark-only AlphaEarth access validation client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.config import get_settings
from app.services.alphaearth_client import AlphaEarthClient


@pytest.mark.asyncio
async def test_validation_skips_when_auth_not_configured() -> None:
    get_settings.cache_clear()
    with patch.dict(
        "os.environ",
        {
            "GEE_PROJECT": "",
            "GEE_ACCESS_TOKEN": "",
            "ALPHAEARTH_COLLECTION": "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
        },
        clear=False,
    ):
        result = await AlphaEarthClient().validate_annual_coverage(year=2024)
    get_settings.cache_clear()

    assert result.status == "skipped"
    assert result.access_ok is False
    assert result.coverage_ok is False
    assert result.reason == "missing_auth_configuration"


@pytest.mark.asyncio
async def test_validation_skips_on_permission_denied() -> None:
    get_settings.cache_clear()
    mock_response = httpx.Response(status_code=403, json={})

    with (
        patch.dict(
            "os.environ",
            {
                "GEE_PROJECT": "my-project",
                "GEE_ACCESS_TOKEN": "secret-token",
                "ALPHAEARTH_COLLECTION": "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
            },
            clear=False,
        ),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await AlphaEarthClient().validate_annual_coverage(year=2024)
    get_settings.cache_clear()

    assert result.status == "skipped"
    assert result.reason == "auth_or_permission_denied"


@pytest.mark.asyncio
async def test_validation_reports_covered_year_when_window_overlaps() -> None:
    get_settings.cache_clear()
    mock_response = httpx.Response(
        status_code=200,
        json={
            "name": "projects/my-project/assets/GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
            "startTime": "2020-01-01T00:00:00Z",
            "endTime": "2025-12-31T23:59:59Z",
        },
    )

    with (
        patch.dict(
            "os.environ",
            {
                "GEE_PROJECT": "my-project",
                "GEE_ACCESS_TOKEN": "secret-token",
                "ALPHAEARTH_COLLECTION": "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
            },
            clear=False,
        ),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await AlphaEarthClient().validate_annual_coverage(year=2024)
    get_settings.cache_clear()

    assert result.status == "ok"
    assert result.access_ok is True
    assert result.coverage_ok is True
    assert result.reason == "covered"


@pytest.mark.asyncio
async def test_validation_skips_when_year_out_of_range() -> None:
    get_settings.cache_clear()
    mock_response = httpx.Response(
        status_code=200,
        json={
            "name": "projects/my-project/assets/GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
            "startTime": "2018-01-01T00:00:00Z",
            "endTime": "2019-12-31T23:59:59Z",
        },
    )

    with (
        patch.dict(
            "os.environ",
            {
                "GEE_PROJECT": "my-project",
                "GEE_ACCESS_TOKEN": "secret-token",
                "ALPHAEARTH_COLLECTION": "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
            },
            clear=False,
        ),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await AlphaEarthClient().validate_annual_coverage(year=2024)
    get_settings.cache_clear()

    assert result.status == "skipped"
    assert result.access_ok is True
    assert result.coverage_ok is False
    assert result.reason == "year_out_of_range"
