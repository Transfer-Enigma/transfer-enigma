import logging

from services.cache.registry import get_cache_registry
from shared.models.cache import CacheEntity
from shared.models.setting import SettingItem
from sqlalchemy.ext.asyncio import AsyncSession

from .get import get_setting, get_setting_with_session

logger = logging.getLogger(__name__)


def _settings_backend():
    return get_cache_registry().backend(CacheEntity.SETTINGS)


async def get_setting_cached(group: str, name: str, *, session: AsyncSession | None = None) -> SettingItem | None:
    backend = _settings_backend()
    cached = await backend.get(group, name, model=SettingItem, many=False)
    if cached:
        return cached

    if session:
        item = await get_setting_with_session(session, group, name)
    else:
        item = await get_setting(group, name)

    if item is not None:
        backend.silent_set_async(group, name, data=item, dump=True)

    return item


async def set_settings_cache(item: SettingItem) -> None:
    backend = _settings_backend()
    await backend.set(item.group, item.name, data=item, dump=True)


async def delete_settings_cache(group: str, name: str) -> None:
    backend = _settings_backend()
    await backend.delete(group, name)
    logger.debug("Settings cache deleted: %s:%s", group, name)
