"""Unit tests for AlphaEarth benchmark client."""

from __future__ import annotations

import os
from unittest.mock import patch

from app.services.alphaearth_client import (
    AlphaEarthAvailability,
    AlphaEarthClient,
)


class TestAlphaEarthClient:
    """Tests for AlphaEarthClient authentication and coverage checks."""

    def test_auth_skip_no_project_id(self) -> None:
        """Authentication should fail gracefully when EE_PROJECT_ID is unset."""
        with patch.dict(os.environ, {"EE_PROJECT_ID": ""}, clear=True):
            client = AlphaEarthClient()
            result = client._authenticate()
            assert result is False
            assert not client._authenticated

    def test_auth_success_with_project_id(self) -> None:
        """Authentication should succeed when EE_PROJECT_ID is set."""
        with patch.dict(os.environ, {"EE_PROJECT_ID": "test-project"}):
            client = AlphaEarthClient()
            result = client._authenticate()
            assert result is True
            assert client._authenticated

    def test_check_coverage_unauthenticated(self) -> None:
        """Coverage check should return skip when not authenticated."""
        client = AlphaEarthClient()
        with patch.object(client, "_authenticate", return_value=False):
            result = client.check_coverage("POINT(-100 40)", 2024)
            assert isinstance(result, AlphaEarthAvailability)
            assert result.available is False
            assert result.skip_reason == "authentication_failed"

    def test_check_coverage_not_implemented(self) -> None:
        """Coverage check should return not_implemented when auth succeeds."""
        client = AlphaEarthClient()
        with patch.object(client, "_authenticate", return_value=True):
            result = client.check_coverage("POINT(-100 40)", 2024)
            assert isinstance(result, AlphaEarthAvailability)
            assert result.available is False
            assert result.skip_reason == "coverage_check_not_implemented"

    def test_fetch_embeddings_unavailable(self) -> None:
        """Fetch should propagate unavailability from coverage check."""
        client = AlphaEarthClient()
        with patch.object(client, "_authenticate", return_value=False):
            result = client.fetch_embeddings("POINT(-100 40)", 2024)
            assert result.available is False
            assert result.skip_reason == "authentication_failed"
