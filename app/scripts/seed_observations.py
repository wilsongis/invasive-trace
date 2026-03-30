"""CLI entry point for observation seeding."""

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory
from app.services.eddmaps_consumer import sync_eddmaps
from app.services.inat_consumer import sync_inaturalist

DEFAULT_BBOX = (-104.0, 33.0, -96.0, 38.0)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed ground-truth observations")
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        default=DEFAULT_BBOX,
        help="Bounding box for sync queries",
    )
    parser.add_argument(
        "--taxon-id",
        action="append",
        type=int,
        default=[],
        help="Taxon ID filter (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch source payloads but rollback DB writes",
    )
    return parser.parse_args()


async def _run() -> int:
    args = _parse_args()
    sync_run_id = str(uuid.uuid4())
    async with async_session_factory() as session:
        inat_stats, eddmaps_stats = await _sync_all(
            session=session,
            bbox=tuple(args.bbox),
            taxon_ids=args.taxon_id,
            sync_run_id=sync_run_id,
        )

        if args.dry_run:
            await session.rollback()
        else:
            await session.commit()

    inserted = inat_stats.records_inserted + eddmaps_stats.records_inserted
    skipped = inat_stats.records_skipped + eddmaps_stats.records_skipped
    for source_name, stats in (("iNaturalist", inat_stats), ("EDDMapS", eddmaps_stats)):
        failure_class = "none" if stats.failures == 0 else "source_failure"
        logger.info(
            "sync_audit sync_run_id=%s roi_id=%s source=%s retry_count=%s "
            "records_inserted=%s records_skipped=%s failure_class=%s",
            sync_run_id,
            "cli_seed",
            source_name,
            stats.retries,
            stats.records_inserted,
            stats.records_skipped,
            failure_class,
        )

    print(
        f"sync_run_id={sync_run_id} sources=2 inserted={inserted} skipped={skipped} "
        f"inat_retries={inat_stats.retries} eddmaps_retries={eddmaps_stats.retries}"
    )
    return 0


async def _sync_all(
    session: AsyncSession,
    bbox: tuple[float, float, float, float],
    taxon_ids: list[int],
    sync_run_id: str,
):
    inat_stats = await sync_inaturalist(
        session=session,
        bbox=bbox,
        taxon_ids=taxon_ids,
        sync_run_id=sync_run_id,
    )
    eddmaps_stats = await sync_eddmaps(
        session=session,
        bbox=bbox,
        taxon_ids=taxon_ids,
        sync_run_id=sync_run_id,
    )
    return inat_stats, eddmaps_stats


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
