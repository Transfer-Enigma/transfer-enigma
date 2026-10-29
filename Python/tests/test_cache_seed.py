from unittest.mock import AsyncMock, patch

import pytest
from data.cache.cache_policies import ensure_cache_policies
from data.cache.seed import ensure_all
from shared.cache import CacheEntity
from shared.cache_policy_definitions import (
    get_cache_policy_definition,
    get_cache_policy_definitions,
)
from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import func, select


async def _policies(sqlite_session):
    result = await sqlite_session.execute(select(CachePolicyModel))
    return list(result.scalars().all())


def _patch_db(sqlite_db):
    return patch("data.cache.cache_policies.get_database", return_value=sqlite_db)


async def test_definitions_are_valid():
    definitions = get_cache_policy_definitions()
    assert len(definitions) == 11
    expected = {
        (None, "rates"): (True, 3600),
        ("fesco", "departures"): (True, 86400),
        ("fesco", "destinations"): (True, 86400),
        ("fesco", "containers"): (True, 86400),
        ("fesco", "routes"): (True, 86400),
        ("fesco", "departures_today"): (True, 600),
        ("fesco", "destinations_today"): (True, 600),
        ("fesco", "containers_today"): (True, 600),
        ("fesco", "routes_today"): (True, 600),
        ("fesco", "points"): (True, 86400),
        ("internal", "points"): (False, 86400),
        ("fesco", "points_today"): (True, 600),
        ("internal", "points_today"): (False, 600),
    }
    seen = set()
    for defn in definitions:
        CacheEntity(defn.entity)
        assert defn.ttl >= 1, f"invalid ttl for {defn.source}:{defn.entity}"
        key = (defn.source, defn.entity)
        assert key not in seen, f"duplicate policy definition for {key}"
        seen.add(key)
        assert get_cache_policy_definition(defn.source, defn.entity) == defn
        exp_enabled, exp_ttl = expected[key]
        assert defn.enabled is exp_enabled
        assert defn.ttl == exp_ttl

    assert get_cache_policy_definition("fesco", "no-such-entity") is None


async def test_ensure_cache_policies_creates_missing(sqlite_db, sqlite_session):
    with _patch_db(sqlite_db):
        await ensure_cache_policies()

    models = await _policies(sqlite_session)
    assert len(models) == len(get_cache_policy_definitions())
    by_entity = {(m.source, m.entity): m for m in models}
    for defn in get_cache_policy_definitions():
        model = by_entity[(defn.source, defn.entity)]
        assert model.enabled is defn.enabled
        assert model.ttl == defn.ttl


async def test_ensure_cache_policies_keeps_existing(sqlite_db, sqlite_session):
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity="routes", enabled=False, ttl=5),
    )
    await sqlite_session.commit()

    with _patch_db(sqlite_db):
        await ensure_cache_policies()

    result = await sqlite_session.execute(
        select(CachePolicyModel).where(
            CachePolicyModel.source == "fesco",
            CachePolicyModel.entity == "routes",
        ),
    )
    model = result.scalar_one()
    assert model.enabled is False
    assert model.ttl == 5


async def test_ensure_cache_policies_is_idempotent(sqlite_db, sqlite_session):
    with _patch_db(sqlite_db):
        await ensure_cache_policies()
        await ensure_cache_policies()

    result = await sqlite_session.execute(select(func.count(CachePolicyModel.id)))
    assert result.scalar_one() == len(get_cache_policy_definitions())


@pytest.mark.asyncio
async def test_ensure_all_seeds_settings_and_policies():
    with (
        patch("data.cache.seed.ensure_settings", new_callable=AsyncMock) as mock_settings,
        patch("data.cache.seed.ensure_cache_policies", new_callable=AsyncMock) as mock_policies,
    ):
        await ensure_all()

    mock_settings.assert_awaited_once_with()
    mock_policies.assert_awaited_once_with()
