"""Integration smoke test — async DB connectivity through the session factory."""

import time

import pytest
from sqlalchemy import text

from app.db import async_session_factory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


async def test_db_connectivity_smoke() -> None:
    """Query pg_stat_activity through the async session; assert the row is returned."""
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT 1 FROM pg_stat_activity LIMIT 1"))
        row = result.fetchone()
    assert row is not None


async def test_db_connectivity_timing() -> None:
    """Async DB smoke test must complete within 5 seconds."""
    start = time.perf_counter()
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1 FROM pg_stat_activity LIMIT 1"))
    elapsed = time.perf_counter() - start
    assert elapsed <= 5.0, f"DB smoke test took {elapsed:.2f}s, expected <= 5s"


async def test_canonical_schema_contract() -> None:
    """Validate canonical Wave 1 schema contract in PostGIS."""
    expected_tables = {
        "regions_of_interest",
        "invasion_predictions",
        "ground_truth_observations",
        "spectral_time_series",
    }
    expected_indexes = {
        "idx_roi_geom",
        "idx_pred_geom",
        "idx_pred_roi",
        "idx_pred_score",
        "idx_gto_geom",
        "idx_gto_source",
        "idx_sts_roi_date",
        "uq_gto_source_external_id_not_null",
    }
    expected_checks = {
        "ck_invasion_predictions_confidence",
        "ck_ground_truth_observations_source",
        "ck_spectral_time_series_platform",
    }

    async with async_session_factory() as session:
        table_rows = await session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """,
            ),
        )
        table_names = {row[0] for row in table_rows.fetchall()}
        assert expected_tables.issubset(table_names)

        srid_rows = await session.execute(
            text(
                """
                SELECT
                    find_srid('public', 'regions_of_interest', 'geom') AS roi_srid,
                    find_srid('public', 'invasion_predictions', 'geom') AS pred_srid,
                    find_srid('public', 'ground_truth_observations', 'geom') AS obs_srid
                """,
            ),
        )
        srid = srid_rows.one()
        assert srid.roi_srid == 4326
        assert srid.pred_srid == 4326
        assert srid.obs_srid == 4326

        index_rows = await session.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                """,
            ),
        )
        index_names = {row[0] for row in index_rows.fetchall()}
        assert expected_indexes.issubset(index_names)

        fk_rows = await session.execute(
            text(
                """
                SELECT conname
                FROM pg_constraint
                WHERE contype = 'f'
                """,
            ),
        )
        fk_names = {row[0] for row in fk_rows.fetchall()}
        assert any("invasion_predictions_roi_id" in name for name in fk_names)
        assert any("spectral_time_series_roi_id" in name for name in fk_names)

        check_rows = await session.execute(
            text(
                """
                SELECT conname
                FROM pg_constraint
                WHERE contype = 'c'
                """,
            ),
        )
        check_names = {row[0] for row in check_rows.fetchall()}
        assert expected_checks.issubset(check_names)
