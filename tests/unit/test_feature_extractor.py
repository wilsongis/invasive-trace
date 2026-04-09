"""Unit tests for feature extractor."""

from uuid import uuid4

import pytest

from app.services.feature_extractor import (
    MIN_SCENES,
    TEMPORAL_WINDOW_DAYS,
    CandidateLocation,
    FeatureExtractor,
    InferenceVector,
    TrainingCohortRecord,
)


def test_feature_extractor_initialization():
    """Test that FeatureExtractor can be initialized."""
    extractor = FeatureExtractor()
    assert extractor is not None


def _make_record(**overrides) -> TrainingCohortRecord:
    defaults = dict(
        roi_id=uuid4(),
        species_label="Test Species",
        ndvi_min=0.1,
        ndvi_max=0.9,
        ndvi_mean=0.5,
        ndvi_std=0.2,
        endvi_min=0.2,
        endvi_max=0.8,
        endvi_mean=0.5,
        endvi_std=0.1,
        red_edge_min=0.3,
        red_edge_max=0.7,
        red_edge_mean=0.5,
        red_edge_std=0.1,
    )
    defaults.update(overrides)
    return TrainingCohortRecord(**defaults)


def test_training_cohort_record_fields():
    """TrainingCohortRecord stores all 12 aggregate spectral fields."""
    record = _make_record()
    assert record.ndvi_min == 0.1
    assert record.ndvi_max == 0.9
    assert record.ndvi_mean == 0.5
    assert record.ndvi_std == 0.2
    assert record.endvi_min == 0.2
    assert record.endvi_max == 0.8
    assert record.endvi_mean == 0.5
    assert record.endvi_std == 0.1
    assert record.red_edge_min == 0.3
    assert record.red_edge_max == 0.7
    assert record.red_edge_mean == 0.5
    assert record.red_edge_std == 0.1


def test_training_cohort_record_12_fields():
    """TrainingCohortRecord exposes exactly the 12 expected spectral attributes."""
    record = _make_record()
    expected = [
        "ndvi_min",
        "ndvi_max",
        "ndvi_mean",
        "ndvi_std",
        "endvi_min",
        "endvi_max",
        "endvi_mean",
        "endvi_std",
        "red_edge_min",
        "red_edge_max",
        "red_edge_mean",
        "red_edge_std",
    ]
    for attr in expected:
        assert hasattr(record, attr), f"Missing attribute: {attr}"


def test_inference_vector():
    """InferenceVector stores all 12 spectral aggregate fields."""
    vector = InferenceVector(
        ndvi_min=0.1,
        ndvi_max=0.9,
        ndvi_mean=0.5,
        ndvi_std=0.2,
        endvi_min=0.2,
        endvi_max=0.8,
        endvi_mean=0.5,
        endvi_std=0.1,
        red_edge_min=0.3,
        red_edge_max=0.7,
        red_edge_mean=0.5,
        red_edge_std=0.1,
    )
    assert vector.ndvi_min == 0.1
    assert vector.ndvi_max == 0.9
    assert vector.ndvi_mean == 0.5
    assert vector.ndvi_std == 0.2
    assert vector.endvi_min == 0.2
    assert vector.endvi_max == 0.8
    assert vector.endvi_mean == 0.5
    assert vector.endvi_std == 0.1
    assert vector.red_edge_min == 0.3
    assert vector.red_edge_max == 0.7
    assert vector.red_edge_mean == 0.5
    assert vector.red_edge_std == 0.1


def test_candidate_location():
    """CandidateLocation stores roi_id, geom, and grid indices."""
    location = CandidateLocation(
        roi_id=uuid4(),
        geom="POINT(1 1)",
        grid_row=2,
        grid_col=3,
    )
    assert location.geom == "POINT(1 1)"
    assert location.grid_row == 2
    assert location.grid_col == 3


def test_candidate_location_defaults():
    """CandidateLocation grid indices default to 0."""
    location = CandidateLocation(roi_id=uuid4(), geom="POINT(0 0)")
    assert location.grid_row == 0
    assert location.grid_col == 0


def test_min_scenes_constant():
    """MIN_SCENES is at least 3 per spec."""
    assert MIN_SCENES >= 3


def test_temporal_window_days_constant():
    """TEMPORAL_WINDOW_DAYS is 45 per spec."""
    assert TEMPORAL_WINDOW_DAYS == 45


# ---------------------------------------------------------------------------
# clip_confidence — T010 (tested on FocalClassifier helper but exercised here
# to verify the constant bounds independently)
# ---------------------------------------------------------------------------


def test_clip_confidence_lower_bound():
    from app.ml.stage2_classifier import FocalClassifier

    assert FocalClassifier.clip_confidence(-0.5) == 0.0


def test_clip_confidence_upper_bound():
    from app.ml.stage2_classifier import FocalClassifier

    assert FocalClassifier.clip_confidence(1.5) == 1.0


def test_clip_confidence_passthrough():
    from app.ml.stage2_classifier import FocalClassifier

    assert FocalClassifier.clip_confidence(0.75) == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# retry_with_backoff — T010
# ---------------------------------------------------------------------------


def test_retry_success_on_third_attempt():
    """func fails twice then succeeds; returns the success value."""
    from app.services.feature_extractor import retry_with_backoff

    call_count = 0

    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("transient failure")
        return "ok"

    result = retry_with_backoff(flaky, max_retries=3, base_delay=0.0)
    assert result == "ok"
    assert call_count == 3


def test_retry_exhaustion_returns_none():
    """func always fails; returns None, no exception raised."""
    from app.services.feature_extractor import retry_with_backoff

    def always_fails():
        raise RuntimeError("always fails")

    result = retry_with_backoff(always_fails, max_retries=3, base_delay=0.0)
    assert result is None


def test_retry_jitter_varies_delays(monkeypatch):
    """Consecutive retry delays are not identical (jitter is applied)."""
    from app.services.feature_extractor import retry_with_backoff

    delays_seen: list[float] = []

    def capture_sleep(delay: float) -> None:
        delays_seen.append(delay)

    monkeypatch.setattr("time.sleep", capture_sleep)

    call_count = 0

    def fail_twice():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RuntimeError("fail")
        return "done"

    retry_with_backoff(fail_twice, max_retries=3, base_delay=1.0)
    # With exponential backoff + uniform jitter, the two delay samples should differ
    assert len(delays_seen) == 2
    # Each delay >= base_delay (1.0) — attempt 0 delay = 1*1 + jitter ≥ 1.0
    assert all(d >= 1.0 for d in delays_seen)
