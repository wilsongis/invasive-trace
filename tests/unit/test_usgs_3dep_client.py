"""Unit tests for USGS 3DEP client (app/services/usgs_3dep_client.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.usgs_3dep_client import (
    ELEVATION_FALLBACK,
    MAX_RETRIES,
    _backoff_delay,
    get_elevation,
)


class TestBackoffDelay:
    def test_delay_increases_with_attempt(self) -> None:
        d0 = _backoff_delay(0)
        d1 = _backoff_delay(1)
        d2 = _backoff_delay(2)
        assert d1 > d0
        assert d2 > d1

    def test_delay_positive(self) -> None:
        for attempt in range(MAX_RETRIES):
            assert _backoff_delay(attempt) > 0


class TestGetElevation:
    @pytest.mark.asyncio
    async def test_returns_elevation_on_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": 1234.5}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_elevation(-104.5, 39.7)

        assert result == 1234.5

    @pytest.mark.asyncio
    async def test_returns_fallback_on_http_error(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        exc = httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=exc)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_elevation(-104.5, 39.7)

        assert result == ELEVATION_FALLBACK

    @pytest.mark.asyncio
    async def test_returns_fallback_on_connection_error(self) -> None:
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("network unreachable"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_elevation(-104.5, 39.7)

        assert result == ELEVATION_FALLBACK

    @pytest.mark.asyncio
    async def test_retries_on_429_then_returns_fallback(self) -> None:
        """Three 429 responses exhaust the retry budget; fallback=0.0 is returned."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as MockClient,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_elevation(-104.5, 39.7)

        assert result == ELEVATION_FALLBACK

    @pytest.mark.asyncio
    async def test_never_raises_unhandled_exception(self) -> None:
        """get_elevation MUST NOT propagate exceptions (NFR-005)."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=RuntimeError("unexpected"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            # Should not raise; must return fallback
            result = await get_elevation(0.0, 0.0)
            assert result == ELEVATION_FALLBACK
