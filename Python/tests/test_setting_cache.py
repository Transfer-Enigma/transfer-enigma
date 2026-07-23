from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from module_shared.cache_settings import get_setting_cached
from module_shared.models.setting import SettingItem
from module_shared.schemas.setting import SettingModel, SettingType


def _mock_cache_controller(get_return=None):
    mock_cc = AsyncMock()
    mock_cc.get_cached = AsyncMock(return_value=get_return)
    mock_cc.set_cache = AsyncMock(return_value=True)
    mock_cc.silent_set_cache_async = MagicMock()
    return mock_cc


def _mock_setting(**overrides) -> SettingItem:
    data = {
        "id": 1, "group": "test_group", "name": "test_key",
        "description": None, "value_type": SettingType.STRING, "value": "test_val",
    }
    data.update(overrides)
    return SettingItem(**data)


@pytest.mark.asyncio
async def test_get_setting_cached_cache_hit(sqlite_session):
    setting = _mock_setting()
    mock_cc = _mock_cache_controller(get_return=setting)

    with patch("module_shared.cache_settings.get_cache_controller", return_value=mock_cc):
        result = await get_setting_cached("test_group", "test_key", session=sqlite_session)

    assert result is not None
    assert result.group == "test_group"
    assert result.name == "test_key"
    assert result.value == "test_val"


@pytest.mark.asyncio
async def test_get_setting_cached_cache_miss_db_found(sqlite_session):
    setting = SettingModel(group="test_group", name="test_key", value_type=SettingType.STRING, value="test_val")
    sqlite_session.add(setting)
    await sqlite_session.commit()

    mock_cc = _mock_cache_controller()

    with patch("module_shared.cache_settings.get_cache_controller", return_value=mock_cc):
        result = await get_setting_cached("test_group", "test_key", session=sqlite_session)

    assert result is not None
    assert result.group == "test_group"
    assert result.name == "test_key"
    assert result.value == "test_val"


@pytest.mark.asyncio
async def test_get_setting_cached_not_found(sqlite_session):
    mock_cc = _mock_cache_controller()

    with patch("module_shared.cache_settings.get_cache_controller", return_value=mock_cc):
        result = await get_setting_cached("nonexistent", "key", session=sqlite_session)

    assert result is None
