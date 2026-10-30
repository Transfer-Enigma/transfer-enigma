import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from data.cache.storage import LocalStorage
from data.fesco.cache import (
    get_containers_backend,
    get_departures_backend,
    get_destinations_backend,
    get_routes_backend,
)
from services.cache.refresh import policy_refresh, refresh_policies, start_policy_refresh
from services.cache.registry import CacheRegistry
from shared.dto.cache import CacheEntity
from shared.orm.cache_policy import CachePolicyModel


async def test_load_keeps_backends_when_policies_do_not_change(sqlite_db, sqlite_session):
    sqlite_session.add(
        CachePolicyModel(source=None, entity=CacheEntity.RATES.value, enabled=True, ttl=60),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with patch("services.cache.registry.get_database", return_value=sqlite_db):
        assert await registry.load() is True
        backend = registry.backend(CacheEntity.RATES)
        assert await registry.load() is False

    assert registry.backend(CacheEntity.RATES) is backend


async def test_load_drops_backends_when_policies_change(sqlite_db, sqlite_session):
    policy = CachePolicyModel(source=None, entity=CacheEntity.RATES.value, enabled=True, ttl=60)
    sqlite_session.add(policy)
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with patch("services.cache.registry.get_database", return_value=sqlite_db):
        await registry.load()
        backend = registry.backend(CacheEntity.RATES)

        policy.ttl = 120
        await sqlite_session.commit()
        assert await registry.load() is True

    assert registry.backend(CacheEntity.RATES) is not backend
    assert registry.backend(CacheEntity.RATES).ttl() == 120


async def test_start_policy_refresh_disabled(monkeypatch):
    monkeypatch.setattr(
        "services.cache.refresh.get_settings",
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

    monkeypatch.setattr("services.cache.refresh.get_cache_registry", lambda: FakeRegistry())
    monkeypatch.setattr("services.cache.refresh.asyncio.sleep", fake_sleep)

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
        "services.cache.refresh.start_policy_refresh",
        lambda: asyncio.create_task(worker()),
    )

    async with policy_refresh():
        await started.wait()

    assert cancelled.is_set()


async def test_today_backends_fall_back_to_base_policy(sqlite_db, sqlite_session):
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.ROUTES, enabled=True, ttl=60),
    )
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.CONTAINERS, enabled=True, ttl=60),
    )
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.DEPARTURES, enabled=True, ttl=60),
    )
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.DESTINATIONS, enabled=True, ttl=60),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with (
        patch("services.cache.registry.get_database", return_value=sqlite_db),
        patch("data.fesco.cache.get_cache_registry", return_value=registry),
    ):
        await registry.load()
        today = datetime.date.today()
        assert get_routes_backend(today).entity == CacheEntity.ROUTES
        assert get_containers_backend(today).entity == CacheEntity.CONTAINERS
        assert get_departures_backend(today).entity == CacheEntity.DEPARTURES
        assert get_destinations_backend(today).entity == CacheEntity.DESTINATIONS


async def test_today_policy_overrides_base_policy(sqlite_db, sqlite_session):
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.ROUTES, enabled=True, ttl=60),
    )
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.ROUTES_TODAY, enabled=True, ttl=600),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with (
        patch("services.cache.registry.get_database", return_value=sqlite_db),
        patch("data.fesco.cache.get_cache_registry", return_value=registry),
    ):
        await registry.load()
        backend = get_routes_backend(datetime.date.today())
        assert backend.entity == CacheEntity.ROUTES_TODAY
        assert backend.is_enabled()
        assert backend.ttl() == 600


async def test_disabled_today_policy_falls_back_to_base(sqlite_db, sqlite_session):
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.ROUTES, enabled=True, ttl=60),
    )
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.ROUTES_TODAY, enabled=False, ttl=600),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with (
        patch("services.cache.registry.get_database", return_value=sqlite_db),
        patch("data.fesco.cache.get_cache_registry", return_value=registry),
    ):
        await registry.load()
        backend = get_routes_backend(datetime.date.today())
        assert backend.entity == CacheEntity.ROUTES
        assert backend.is_enabled()
        assert backend.ttl() == 60
