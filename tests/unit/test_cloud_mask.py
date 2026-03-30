"""Unit tests for QA60 cloud masking behavior."""

from __future__ import annotations

import numpy as np

from app.services.cloud_mask import compute_cloud_fraction, compute_cloud_fraction_from_array


def test_clear_scene() -> None:
    qa60 = np.zeros((4, 4), dtype=np.uint16)

    cloud_fraction, is_masked = compute_cloud_fraction_from_array(qa60)

    assert cloud_fraction == 0.0
    assert is_masked is False


def test_fully_clouded_scene() -> None:
    qa60 = np.full((4, 4), 1 << 10, dtype=np.uint16)

    cloud_fraction, is_masked = compute_cloud_fraction_from_array(qa60)

    assert cloud_fraction == 1.0
    assert is_masked is True


def test_threshold_boundary_at_twenty_percent() -> None:
    qa60 = np.zeros((10, 10), dtype=np.uint16)
    qa60.flat[:20] = 1 << 10

    cloud_fraction, is_masked = compute_cloud_fraction_from_array(qa60)

    assert cloud_fraction == 0.2
    assert is_masked is False


def test_threshold_boundary_above_twenty_percent() -> None:
    qa60 = np.zeros((10, 10), dtype=np.uint16)
    qa60.flat[:21] = 1 << 10

    cloud_fraction, is_masked = compute_cloud_fraction_from_array(qa60)

    assert cloud_fraction == 0.21
    assert is_masked is True


def test_cirrus_bit_counts_as_cloud() -> None:
    qa60 = np.full((4, 4), 1 << 11, dtype=np.uint16)

    cloud_fraction, is_masked = compute_cloud_fraction_from_array(qa60)

    assert cloud_fraction == 1.0
    assert is_masked is True


def test_missing_qa60_href_defaults_to_masked() -> None:
    cloud_fraction, is_masked = compute_cloud_fraction(None, (-104.5, 40.0, -104.4, 40.1))

    assert cloud_fraction == 1.0
    assert is_masked is True
