import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from data.cache.refresh import policy_refresh, refresh_policies, start_policy_refresh
from data.cache.registry import CacheRegistry
from shared.cache import CacheEntity, LocalStorage
from shared.orm.cache_policy import CachePolicyModel


async def test_load_keeps_backends_when_policies_do_not_change(sqlite_db, sqlite_session):
    sqlite_session.add(
        CachePolicyModel(source=None, entity=CacheEntity.RATES.value, enabled=True, ttl=60),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with patch("data.cache.registry.get_database", return_value=sqlite_db):
        assert await registry.load() is True
        backend = registry.backend(CacheEntity.RATES)
        assert await registry.load() is False

    assert registry.backend(CacheEntity.RATES) is backend


async def test_load_drops_backends_when_policies_change(sqlite_db, sqlite_session):
    policy = CachePolicyModel(source=None, entity=CacheEntity.RATES.value, enabled=True, ttl=60)
    sqlite_session.add(policy)
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with patch("data.cache.registry.get_database", return_value=sqlite_db):
        await registry.load()
        backend = registry.backend(CacheEntity.RATES)

        policy.ttl = 120
        await sqlite_session.commit()
        assert await registry.load() is True

    assert registry.backend(CacheEntity.RATES) is not backend
    assert registry.backend(CacheEntity.RATES).ttl() == 120


async def test_start_policy_refresh_disabled(monkeypatch):
    monkeypatch.setattr(
        "data.cache.refresh.get_settings",
        lambda: SimpleNamespace(CACHE_POLICIES_REFRESH_INTERVAL_SECONDS=0),
    )
    assert start_policy_refresh() is None


async def test_refresh_policies_reloads_until_cancelled(monkeypatch):
    calls = []

    class FakeRegistry:
        async def load(self):
            calls.append(1)

    async def fake_sleep(_interval):
        if len(calls) >= 3:
            raise asyncio.CancelledError

    monkeypatch.setattr("data.cache.refresh.get_cache_registry", lambda: FakeRegistry())
    monkeypatch.setattr("data.cache.refresh.asyncio.sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await refresh_policies(10)

    assert len(calls) == 3


async def test_policy_refresh_cancels_the_started_task(monkeypatch):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def worker():
        started.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(
        "data.cache.refresh.start_policy_refresh",
        lambda: asyncio.create_task(worker()),
    )

    async with policy_refresh():
        await started.wait()

    assert cancelled.is_set()
