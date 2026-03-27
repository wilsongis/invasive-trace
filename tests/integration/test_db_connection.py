"""Integration smoke test — async DB connectivity through the session factory."""

import time

import pytest
from sqlalchemy import text

from app.db import async_session_factory

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_db_connectivity_smoke() -> None:
    """Query pg_stat_activity through the async session; assert the row is returned."""
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT 1 FROM pg_stat_activity LIMIT 1"))
        row = result.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_db_connectivity_timing() -> None:
    """Async DB smoke test must complete within 5 seconds."""
    start = time.perf_counter()
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1 FROM pg_stat_activity LIMIT 1"))
    elapsed = time.perf_counter() - start
    assert elapsed <= 5.0, f"DB smoke test took {elapsed:.2f}s, expected <= 5s"
