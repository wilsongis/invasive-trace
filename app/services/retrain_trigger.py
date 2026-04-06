"""Retraining trigger service for HITL dashboard.

Monitors the count of validated predictions and signals when the
retraining threshold is reached.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import InvasionPrediction

logger = logging.getLogger(__name__)

RETRAIN_THRESHOLD = 50


async def check_retrain_trigger(db: AsyncSession) -> bool:
    """Check whether the number of validated predictions meets the retraining threshold.

    Queries ``invasion_predictions`` for ``COUNT(*) WHERE validated IS NOT NULL``.
    If the count >= ``RETRAIN_THRESHOLD`` (50), logs ``RETRAINING_TRIGGERED`` at
    INFO level and returns ``True``; otherwise returns ``False``.

    Args:
        db: Async SQLAlchemy session.

    Returns:
        True if the retraining threshold is met, False otherwise.
    """
    stmt = (
        select(func.count())
        .select_from(InvasionPrediction)
        .where(InvasionPrediction.validated.isnot(None))
    )
    result = await db.execute(stmt)
    reviewed_count = result.scalar_one() or 0

    if reviewed_count >= RETRAIN_THRESHOLD:
        logger.info(
            "RETRAINING_TRIGGERED: %d predictions validated (threshold: %d)",
            reviewed_count,
            RETRAIN_THRESHOLD,
        )
        return True

    return False
