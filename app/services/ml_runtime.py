"""Model runtime contracts: version registry and value-clamping helpers."""

from __future__ import annotations

# Model version registry — must match AGENTS.md Section 6 exactly
STAGE1_VERSION = "anomaly-v0.1.0"
STAGE2_VERSION = "rf-v0.1.0"
STAGE3_VERSION = "unet-v0.1.0"


def clamp_confidence(value: float) -> float:
    """Clamp confidence to [0.0, 1.0] before DB write (FR-009, NFR-001)."""
    return max(0.0, min(1.0, value))


def clamp_hotspot_score(value: float) -> float:
    """Clamp hotspot_score to [0.0, 1.0] before DB write (FR-015, NFR-002)."""
    return max(0.0, min(1.0, value))
