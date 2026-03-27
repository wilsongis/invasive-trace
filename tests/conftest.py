"""Shared pytest fixtures and configuration for all test tiers."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as requiring external services (e.g. PostGIS). "
        "Deselect with: pytest -m 'not integration'",
    )
