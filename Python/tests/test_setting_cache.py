from unittest.mock import patch

import pytest
from data.cache.storage import LocalStorage
from data.setings.cached import delete_settings_cache, get_setting_cached
from services.cache.registry import CacheRegistry
from shared.dto.cache import CacheEntity
from shared.dto.setting import SettingItem
from shared.orm.cache_policy import CachePolicyModel
from shared.orm.setting import SettingModel, SettingType

SETTINGS_CACHE_SOURCE = None


def _mock_setting(**overrides) -> SettingItem:
    data = {
        "group": "test_group", "name": "test_key",
        "value_type": SettingType.STRING, "value": "test_val",
    }
    data.update(overrides)
    return SettingItem(**data)


async def _registry(sqlite_db, sqlite_session, *, enabled=True, ttl=60) -> CacheRegistry:
    """A registry with the settings policy stored in the database."""
    sqlite_session.add(
        CachePolicyModel(
            source=SETTINGS_CACHE_SOURCE,
            entity=CacheEntity.SETTINGS.value,
            enabled=enabled,
            ttl=ttl,
        ),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with patch("services.cache.registry.get_database", return_value=sqlite_db):
        await registry.load()
    return registry


@pytest.mark.asyncio
async def test_get_setting_cached_cache_hit(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    await registry.backend(CacheEntity.SETTINGS).set(
        "test_group", "test_key",
        data=_mock_setting(), dump=True,
    )

    with patch("data.setings.cached.get_cache_registry", return_value=registry):
        result = await get_setting_cached("test_group", "test_key", session=sqlite_session)

    assert result is not None
    assert result.group == "test_group"
    assert result.name == "test_key"
    assert result.value == "test_val"


@pytest.mark.asyncio
async def test_get_setting_cached_cache_miss_db_found(sqlite_db, sqlite_session):
    setting = SettingModel(group="test_group", name="test_key", value_type=SettingType.STRING, value="test_val")
    sqlite_session.add(setting)
    await sqlite_session.commit()

    registry = await _registry(sqlite_db, sqlite_session)

    with patch("data.setings.cached.get_cache_registry", return_value=registry):
        result = await get_setting_cached("test_group", "test_key", session=sqlite_session)

    assert result is not None
    assert result.group == "test_group"
    assert result.name == "test_key"
    assert result.value == "test_val"


@pytest.mark.asyncio
async def test_get_setting_cached_not_found(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)

    with patch("data.setings.cached.get_cache_registry", return_value=registry):
        result = await get_setting_cached("nonexistent", "key", session=sqlite_session)

    assert result is None


@pytest.mark.asyncio
async def test_get_setting_cached_without_policy_is_not_cached(sqlite_db, sqlite_session):
    """Without a policy the value is read from the database and not cached."""
    setting = SettingModel(group="test_group", name="test_key", value_type=SettingType.STRING, value="test_val")
    sqlite_session.add(setting)
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())

    with patch("data.setings.cached.get_cache_registry", return_value=registry):
        result = await get_setting_cached("test_group", "test_key", session=sqlite_session)

    assert result is not None
    assert result.value == "test_val"

    backend = registry.backend(CacheEntity.SETTINGS)
    assert await backend.get("test_group", "test_key") is None


@pytest.mark.asyncio
async def test_delete_settings_cache_removes_a_value(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    backend = registry.backend(CacheEntity.SETTINGS)
    await backend.set("test_group", "test_key", data=_mock_setting(), dump=True)

    with patch("data.setings.cached.get_cache_registry", return_value=registry):
        await delete_settings_cache("test_group", "test_key")

    assert await backend.get("test_group", "test_key") is None
