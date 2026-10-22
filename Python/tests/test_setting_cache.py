from unittest.mock import patch

import pytest
from data.cache.registry import CacheRegistry
from data.cache.settings import get_setting_cached
from shared.cache import CacheEntity, LocalStorage
from shared.dto.setting import SettingItem
from shared.orm.cache_policy import CachePolicyModel
from shared.orm.setting import SettingModel, SettingType

SETTINGS_SOURCE = "internal"


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
            source=SETTINGS_SOURCE,
            entity=CacheEntity.SETTINGS.value,
            enabled=enabled,
            ttl=ttl,
        ),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with patch("data.cache.registry.get_database", return_value=sqlite_db):
        await registry.load()
    return registry


@pytest.mark.asyncio
async def test_get_setting_cached_cache_hit(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    await registry.backend(SETTINGS_SOURCE).set(
        CacheEntity.SETTINGS, "test_group", "test_key",
        data=_mock_setting(), dump=True,
    )

    with patch("data.cache.settings.get_cache_registry", return_value=registry):
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

    with patch("data.cache.settings.get_cache_registry", return_value=registry):
        result = await get_setting_cached("test_group", "test_key", session=sqlite_session)

    assert result is not None
    assert result.group == "test_group"
    assert result.name == "test_key"
    assert result.value == "test_val"


@pytest.mark.asyncio
async def test_get_setting_cached_not_found(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)

    with patch("data.cache.settings.get_cache_registry", return_value=registry):
        result = await get_setting_cached("nonexistent", "key", session=sqlite_session)

    assert result is None


@pytest.mark.asyncio
async def test_get_setting_cached_without_policy_is_not_cached(sqlite_db, sqlite_session):
    """Without a policy the value is read from the database and not cached."""
    setting = SettingModel(group="test_group", name="test_key", value_type=SettingType.STRING, value="test_val")
    sqlite_session.add(setting)
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())

    with patch("data.cache.settings.get_cache_registry", return_value=registry):
        result = await get_setting_cached("test_group", "test_key", session=sqlite_session)

    assert result is not None
    assert result.value == "test_val"

    backend = registry.backend(SETTINGS_SOURCE)
    assert await backend.keys(CacheEntity.SETTINGS) == []
