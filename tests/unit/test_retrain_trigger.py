"""Unit tests for the retraining trigger service."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.retrain_trigger import RETRAIN_THRESHOLD, check_retrain_trigger


class TestRetrainTrigger:
    """Tests for check_retrain_trigger()."""

    @pytest.mark.asyncio
    async def test_returns_false_below_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """49 validated rows should return False and not emit RETRAINING_TRIGGERED log."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 49

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with caplog.at_level(logging.INFO):
            result = await check_retrain_trigger(mock_db)

        assert result is False
        assert "RETRAINING_TRIGGERED" not in caplog.text

    @pytest.mark.asyncio
    async def test_returns_true_at_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """50 validated rows should return True and emit RETRAINING_TRIGGERED log."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 50

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with caplog.at_level(logging.INFO):
            result = await check_retrain_trigger(mock_db)

        assert result is True
        assert "RETRAINING_TRIGGERED" in caplog.text

    @pytest.mark.asyncio
    async def test_returns_true_above_threshold_idempotent(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """51+ validated rows should return True (idempotent)."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 75

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with caplog.at_level(logging.INFO):
            result = await check_retrain_trigger(mock_db)

        assert result is True
        assert "RETRAINING_TRIGGERED" in caplog.text

    @pytest.mark.asyncio
    async def test_returns_false_for_zero_validated(self, caplog: pytest.LogCaptureFixture) -> None:
        """0 validated rows should return False."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with caplog.at_level(logging.INFO):
            result = await check_retrain_trigger(mock_db)

        assert result is False
        assert "RETRAINING_TRIGGERED" not in caplog.text

    def test_retrain_threshold_constant_is_50(self) -> None:
        """RETRAIN_THRESHOLD should be 50 per spec."""
        assert RETRAIN_THRESHOLD == 50
