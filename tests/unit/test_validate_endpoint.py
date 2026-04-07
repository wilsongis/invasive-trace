"""Unit tests for PATCH /api/v1/predictions/{id}/validate endpoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from app.api.v1 import predictions as predictions_module
from app.main import app


@pytest.fixture
def mock_prediction() -> MagicMock:
    """Create a mock InvasionPrediction instance."""
    mock = MagicMock()
    mock.id = uuid.uuid4()
    mock.roi_id = uuid.uuid4()
    mock.species_label = "Bromus tectorum"
    mock.confidence = 0.87
    mock.hotspot_score = 0.72
    mock.model_version = "rf-v0.1.0"
    mock.predicted_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    mock.validated = None
    mock.validator_notes = None
    return mock


class TestValidatePredictionEndpoint:
    """Tests for PATCH /api/v1/predictions/{id}/validate."""

    def test_validate_returns_422_for_missing_validated(self) -> None:
        """PATCH without validated field should return 422."""
        with TestClient(app) as client:
            res = client.patch(
                f"/api/v1/predictions/{uuid.uuid4()}/validate",
                json={"validator_notes": "some notes"},
            )
        assert res.status_code == 422

    def test_validate_returns_422_for_non_boolean_validated(self) -> None:
        """PATCH with non-boolean validated should return 422."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()

        mock_session = MagicMock(spec=AsyncSession)
        mock_session.execute.return_value = mock_result

        async def mock_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        app.dependency_overrides[predictions_module.get_db] = mock_get_db

        with TestClient(app) as client:
            res = client.patch(
                f"/api/v1/predictions/{uuid.uuid4()}/validate",
                json={"validated": "yes"},
            )
        assert res.status_code == 422

        app.dependency_overrides.pop(predictions_module.get_db, None)

    def test_validate_returns_422_for_invalid_uuid(self) -> None:
        """PATCH with invalid UUID should return 422."""
        with TestClient(app) as client:
            res = client.patch(
                "/api/v1/predictions/not-a-uuid/validate",
                json={"validated": True},
            )
        assert res.status_code == 422

    def test_validate_sets_validated_true_and_persists_notes(
        self, mock_prediction: MagicMock
    ) -> None:
        """PATCH with validated=true should update the row and return 200."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prediction

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.return_value = mock_result

        async def mock_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        app.dependency_overrides[predictions_module.get_db] = mock_get_db

        with patch(
            "app.api.v1.predictions.check_retrain_trigger",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with TestClient(app) as client:
                res = client.patch(
                    f"/api/v1/predictions/{mock_prediction.id}/validate",
                    json={"validated": True, "validator_notes": "confirmed via field survey"},
                )

            assert res.status_code == 200
            body = res.json()
            assert body["validated"] is True
            assert body["validator_notes"] == "confirmed via field survey"
            assert body["id"] == str(mock_prediction.id)
            assert body["retraining_triggered"] is False

        app.dependency_overrides.pop(predictions_module.get_db, None)

    def test_validate_returns_404_for_unknown_id(self) -> None:
        """PATCH with unknown prediction ID should return 404."""
        unknown_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.return_value = mock_result

        async def mock_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        app.dependency_overrides[predictions_module.get_db] = mock_get_db

        with TestClient(app) as client:
            res = client.patch(
                f"/api/v1/predictions/{unknown_id}/validate",
                json={"validated": True},
            )

            assert res.status_code == 404
            assert "not found" in res.json()["detail"].lower()

        app.dependency_overrides.pop(predictions_module.get_db, None)

    def test_validate_sets_validated_false(self, mock_prediction: MagicMock) -> None:
        """PATCH with validated=false should reject the prediction."""
        mock_prediction.validated = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prediction

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.return_value = mock_result

        async def mock_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        app.dependency_overrides[predictions_module.get_db] = mock_get_db

        with patch(
            "app.api.v1.predictions.check_retrain_trigger",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with TestClient(app) as client:
                res = client.patch(
                    f"/api/v1/predictions/{mock_prediction.id}/validate",
                    json={"validated": False, "validator_notes": "misclassified"},
                )

            assert res.status_code == 200
            body = res.json()
            assert body["validated"] is False
            assert body["validator_notes"] == "misclassified"

        app.dependency_overrides.pop(predictions_module.get_db, None)

    def test_validate_triggers_retraining_at_threshold(self, mock_prediction: MagicMock) -> None:
        """PATCH should return retraining_triggered=True when threshold is met."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prediction

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.return_value = mock_result

        async def mock_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        app.dependency_overrides[predictions_module.get_db] = mock_get_db

        with patch(
            "app.api.v1.predictions.check_retrain_trigger",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with TestClient(app) as client:
                res = client.patch(
                    f"/api/v1/predictions/{mock_prediction.id}/validate",
                    json={"validated": True},
                )

            assert res.status_code == 200
            body = res.json()
            assert body["retraining_triggered"] is True

        app.dependency_overrides.pop(predictions_module.get_db, None)
