"""Unit tests for SCL-based cloud masking behavior."""

from __future__ import annotations

import numpy as np

from app.services.cloud_mask import compute_cloud_fraction, compute_cloud_fraction_from_scl

# SCL class values per Sentinel-2 L2A spec
SCL_CLEAR = 4  # vegetation
SCL_CLOUD_MED = 8  # cloud medium probability
SCL_CLOUD_HIGH = 9  # cloud high probability
SCL_THIN_CIRRUS = 10  # thin cirrus
SCL_SNOW = 11  # snow/ice


def test_clear_scene() -> None:
    """All vegetation pixels should yield zero cloud fraction."""
    scl = np.full((4, 4), SCL_CLEAR, dtype=np.uint8)

    cloud_fraction, is_masked = compute_cloud_fraction_from_scl(scl)

    assert cloud_fraction == 0.0
    assert is_masked is False


def test_fully_clouded_scene() -> None:
    """All cloud-medium pixels should yield full cloud fraction."""
    scl = np.full((4, 4), SCL_CLOUD_MED, dtype=np.uint8)

    cloud_fraction, is_masked = compute_cloud_fraction_from_scl(scl)

    assert cloud_fraction == 1.0
    assert is_masked is True


def test_threshold_boundary_at_twenty_percent() -> None:
    """Exactly 20% cloud pixels should NOT be masked."""
    scl = np.full((10, 10), SCL_CLEAR, dtype=np.uint8)
    scl.flat[:20] = SCL_CLOUD_HIGH

    cloud_fraction, is_masked = compute_cloud_fraction_from_scl(scl)

    assert cloud_fraction == 0.2
    assert is_masked is False


def test_threshold_boundary_above_twenty_percent() -> None:
    """21% cloud pixels should be masked."""
    scl = np.full((10, 10), SCL_CLEAR, dtype=np.uint8)
    scl.flat[:21] = SCL_CLOUD_HIGH

    cloud_fraction, is_masked = compute_cloud_fraction_from_scl(scl)

    assert cloud_fraction == 0.21
    assert is_masked is True


def test_thin_cirrus_counts_as_cloud() -> None:
    """Thin cirrus class should be counted as cloud."""
    scl = np.full((4, 4), SCL_THIN_CIRRUS, dtype=np.uint8)

    cloud_fraction, is_masked = compute_cloud_fraction_from_scl(scl)

    assert cloud_fraction == 1.0
    assert is_masked is True


def test_snow_counts_as_cloud() -> None:
    """Snow/ice class should be counted as cloud for conservative masking."""
    scl = np.full((4, 4), SCL_SNOW, dtype=np.uint8)

    cloud_fraction, is_masked = compute_cloud_fraction_from_scl(scl)

    assert cloud_fraction == 1.0
    assert is_masked is True


def test_missing_scl_href_defaults_to_masked() -> None:
    """Missing SCL asset should default to fully masked."""
    cloud_fraction, is_masked = compute_cloud_fraction(None, (-104.5, 40.0, -104.4, 40.1))

    assert cloud_fraction == 1.0
    assert is_masked is True
