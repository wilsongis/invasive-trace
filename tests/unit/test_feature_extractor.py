"""Unit tests for Stage 2 feature extractor (app/services/feature_extractor.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from app.services.feature_extractor import build_feature_vector


class TestBuildFeatureVector:
    @pytest.mark.asyncio
    async def test_returns_shape_1_4(self) -> None:
        with patch(
            "app.services.feature_extractor.get_elevation", new_callable=AsyncMock
        ) as mock_elev:
            mock_elev.return_value = 500.0
            vec = await build_feature_vector(
                ndvi=0.6, endvi=0.5, red_edge=0.4, lon=-104.5, lat=39.7
            )

        assert vec.shape == (1, 4)
        assert vec.dtype == np.float32

    @pytest.mark.asyncio
    async def test_feature_order_ndvi_endvi_rededge_elevation(self) -> None:
        with patch(
            "app.services.feature_extractor.get_elevation", new_callable=AsyncMock
        ) as mock_elev:
            mock_elev.return_value = 1234.0
            vec = await build_feature_vector(ndvi=0.6, endvi=0.5, red_edge=0.4, lon=0.0, lat=0.0)

        assert float(vec[0, 0]) == pytest.approx(0.6, rel=1e-4)
        assert float(vec[0, 1]) == pytest.approx(0.5, rel=1e-4)
        assert float(vec[0, 2]) == pytest.approx(0.4, rel=1e-4)
        assert float(vec[0, 3]) == pytest.approx(1234.0, rel=1e-4)

    @pytest.mark.asyncio
    async def test_none_spectral_values_become_zero(self) -> None:
        with patch(
            "app.services.feature_extractor.get_elevation", new_callable=AsyncMock
        ) as mock_elev:
            mock_elev.return_value = 0.0
            vec = await build_feature_vector(ndvi=None, endvi=None, red_edge=None, lon=0.0, lat=0.0)

        assert float(vec[0, 0]) == 0.0
        assert float(vec[0, 1]) == 0.0
        assert float(vec[0, 2]) == 0.0

    @pytest.mark.asyncio
    async def test_elevation_fallback_propagates_to_feature(self) -> None:
        """When 3DEP returns 0.0 fallback, feature[3] must be 0.0."""
        with patch(
            "app.services.feature_extractor.get_elevation", new_callable=AsyncMock
        ) as mock_elev:
            mock_elev.return_value = 0.0
            vec = await build_feature_vector(
                ndvi=0.5, endvi=0.4, red_edge=0.3, lon=-105.0, lat=40.0
            )

        assert float(vec[0, 3]) == 0.0
