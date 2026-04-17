"""Unit tests for benchmark cohort assembly and deterministic split alignment."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.benchmark_dataset import align_train_test_split, assemble_benchmark_cohort


class TestAlignTrainTestSplit:
    def test_split_is_deterministic_for_same_seed(self) -> None:
        ids = [uuid4() for _ in range(12)]

        split_a = align_train_test_split(ids, test_fraction=0.25, split_seed=99)
        split_b = align_train_test_split(ids, test_fraction=0.25, split_seed=99)

        assert split_a == split_b

    def test_split_changes_with_seed(self) -> None:
        ids = [uuid4() for _ in range(12)]

        split_a = align_train_test_split(ids, test_fraction=0.25, split_seed=99)
        split_b = align_train_test_split(ids, test_fraction=0.25, split_seed=123)

        assert split_a != split_b

    def test_single_sample_stays_train(self) -> None:
        sample_id = uuid4()

        split_map = align_train_test_split([sample_id], test_fraction=0.5)

        assert split_map[sample_id] == "train"

    def test_invalid_fraction_raises(self) -> None:
        ids = [uuid4(), uuid4()]

        with pytest.raises(ValueError):
            align_train_test_split(ids, test_fraction=1.0)


class TestAssembleBenchmarkCohort:
    @pytest.mark.asyncio
    async def test_assemble_cohort_uses_roi_year_rows_and_returns_counts(self) -> None:
        roi_id = uuid4()
        roi = SimpleNamespace(id=roi_id, geom=object())

        row_a = SimpleNamespace(id=uuid4(), species_label="Bromus tectorum", lon=-101.0, lat=35.0)
        row_b = SimpleNamespace(id=uuid4(), species_label="Bromus tectorum", lon=-101.1, lat=35.1)
        row_c = SimpleNamespace(
            id=uuid4(),
            species_label="Tamarix ramosissima",
            lon=-101.2,
            lat=35.2,
        )

        session = AsyncMock()
        session.get = AsyncMock(return_value=roi)
        execute_result = MagicMock()
        execute_result.all.return_value = [row_a, row_b, row_c]
        session.execute = AsyncMock(return_value=execute_result)

        cohort = await assemble_benchmark_cohort(
            session=session,
            roi_id=roi_id,
            year=2024,
            test_fraction=0.34,
            split_seed=11,
        )

        assert cohort.roi_id == roi_id
        assert cohort.year == 2024
        assert cohort.sample_count == 3
        assert cohort.train_count + cohort.test_count == 3
        assert cohort.labels == ["Bromus tectorum", "Tamarix ramosissima"]
        assert all(sample.split in {"train", "test"} for sample in cohort.samples)

    @pytest.mark.asyncio
    async def test_assemble_cohort_raises_when_roi_missing(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="ROI"):
            await assemble_benchmark_cohort(session=session, roi_id=uuid4(), year=2024)

    @pytest.mark.asyncio
    async def test_assemble_cohort_raises_when_no_rows(self) -> None:
        roi_id = uuid4()
        roi = SimpleNamespace(id=roi_id, geom=object())

        session = AsyncMock()
        session.get = AsyncMock(return_value=roi)
        execute_result = MagicMock()
        execute_result.all.return_value = []
        session.execute = AsyncMock(return_value=execute_result)

        with pytest.raises(ValueError, match="No labeled observations"):
            await assemble_benchmark_cohort(session=session, roi_id=roi_id, year=2024)
