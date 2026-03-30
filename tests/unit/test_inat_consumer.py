"""Unit tests for iNaturalist consumer retry behavior."""

from __future__ import annotations

import httpx
import pytest

from app.services.inat_consumer import _request_with_retry


@pytest.mark.asyncio
async def test_inat_retries_then_succeeds() -> None:
    attempts = {"count": 0}
    delays: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"results": []})

    async def fake_sleep(value: float) -> None:
        delays.append(value)

    jitter_values = iter([0.0, 1.0])

    def fake_jitter() -> float:
        return next(jitter_values)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        payload, retries = await _request_with_retry(
            client,
            params={},
            sleep=fake_sleep,
            jitter_fn=fake_jitter,
        )

    assert payload == {"results": []}
    assert retries == 2
    assert delays == [0.25, 0.55]


@pytest.mark.asyncio
async def test_inat_fails_after_retry_budget() -> None:
    sleeps: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={})

    async def fake_sleep(value: float) -> None:
        sleeps.append(value)

    def fake_jitter() -> float:
        return 0.0

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        payload, retries = await _request_with_retry(
            client,
            params={},
            sleep=fake_sleep,
            jitter_fn=fake_jitter,
        )

    assert payload is None
    assert retries == 3
    assert sleeps == [0.25, 0.5, 1.0]
