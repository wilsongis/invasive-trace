"""Unit tests for spectral index formulas."""

from __future__ import annotations

import numpy as np

from app.services.indices import compute_endvi, compute_ndvi, compute_red_edge


def test_ndvi_formula() -> None:
    b08 = np.array([[0.8, 0.7], [0.6, 0.5]], dtype=np.float32)
    b04 = np.array([[0.2, 0.2], [0.3, 0.2]], dtype=np.float32)

    result = compute_ndvi(b08, b04)

    assert result is not None
    assert -1.0 <= result <= 1.0


def test_endvi_formula() -> None:
    b08 = np.array([[0.8, 0.7], [0.6, 0.5]], dtype=np.float32)
    b03 = np.array([[0.3, 0.3], [0.2, 0.2]], dtype=np.float32)
    b04 = np.array([[0.2, 0.2], [0.3, 0.2]], dtype=np.float32)

    result = compute_endvi(b08, b03, b04)

    assert result is not None
    assert -1.0 <= result <= 1.0


def test_red_edge_formula() -> None:
    b8a = np.array([[0.9, 0.8], [0.7, 0.6]], dtype=np.float32)
    b05 = np.array([[0.3, 0.3], [0.3, 0.2]], dtype=np.float32)

    result = compute_red_edge(b8a, b05)

    assert result is not None
    assert -1.0 <= result <= 20.0


def test_zero_denominator_guard() -> None:
    b08 = np.zeros((2, 2), dtype=np.float32)
    b04 = np.zeros((2, 2), dtype=np.float32)

    result = compute_ndvi(b08, b04)

    assert result == 0.0


def test_all_nodata_returns_none() -> None:
    nodata = np.array([[np.nan, np.nan], [np.nan, np.nan]], dtype=np.float32)

    result = compute_ndvi(nodata, nodata)

    assert result is None
