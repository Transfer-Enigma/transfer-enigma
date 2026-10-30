from unittest.mock import patch

import pytest
from data.cache.cache_policies import ensure_cache_policies
from shared.dto.cache import CacheEntity
from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import func, select


async def _policies(sqlite_session):
    result = await sqlite_session.execute(select(CachePolicyModel))
    return list(result.scalars().all())


def _patch_db(sqlite_db):
    return patch("data.cache.cache_policies.get_database", return_value=sqlite_db)


async def test_ensure_cache_policies_creates_missing(sqlite_db, sqlite_session):
    with _patch_db(sqlite_db):
        await ensure_cache_policies()

    models = await _policies(sqlite_session)
    # 22 policies: rates, settings + 10 multi-source × 2 sources
    assert len(models) == 22
    by_entity = {(m.source, m.entity): m for m in models}
    expected_ttl = {
        (None, CacheEntity.RATES): 3600,
        (None, CacheEntity.SETTINGS): 3600,
        ("fesco", CacheEntity.DEPARTURES): 43200,
        ("internal", CacheEntity.DEPARTURES): 86400,
        ("fesco", CacheEntity.DESTINATIONS): 43200,
        ("internal", CacheEntity.DESTINATIONS): 86400,
        ("fesco", CacheEntity.CONTAINERS): 86400,
        ("internal", CacheEntity.CONTAINERS): 86400,
        ("fesco", CacheEntity.ROUTES): 43200,
        ("internal", CacheEntity.ROUTES): 86400,
        ("fesco", CacheEntity.DEPARTURES_TODAY): 86400,
        ("internal", CacheEntity.DEPARTURES_TODAY): 86400,
        ("fesco", CacheEntity.DESTINATIONS_TODAY): 86400,
        ("internal", CacheEntity.DESTINATIONS_TODAY): 86400,
        ("fesco", CacheEntity.CONTAINERS_TODAY): 86400,
        ("internal", CacheEntity.CONTAINERS_TODAY): 86400,
        ("fesco", CacheEntity.ROUTES_TODAY): 43200,
        ("internal", CacheEntity.ROUTES_TODAY): 43200,
        ("fesco", CacheEntity.POINTS): 86400,
        ("internal", CacheEntity.POINTS): 86400,
        ("fesco", CacheEntity.POINTS_TODAY): 86400,
        ("internal", CacheEntity.POINTS_TODAY): 86400,
    }
    for key, expected in expected_ttl.items():
        model = by_entity[key]
        assert model.ttl == expected, f"{key}: expected TTL={expected}, got {model.ttl}"


async def test_ensure_cache_policies_keeps_existing(sqlite_db, sqlite_session):
    sqlite_session.add(
        CachePolicyModel(source="fesco", entity=CacheEntity.ROUTES, enabled=False, ttl=5),
    )
    await sqlite_session.commit()

    with _patch_db(sqlite_db):
        await ensure_cache_policies()

    result = await sqlite_session.execute(
        select(CachePolicyModel).where(
            CachePolicyModel.source == "fesco",
            CachePolicyModel.entity == CacheEntity.ROUTES,
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
    assert result.scalar_one() == 22


@pytest.mark.asyncio
async def test_seed_cache_services_call_data_layer():
    """Test that seed services exist and are importable."""
    from services.cache.seed import do_seed as seed_cache_policies
    from services.settings.seed import do_seed as seed_settings
    assert callable(seed_cache_policies)
    assert callable(seed_settings)
