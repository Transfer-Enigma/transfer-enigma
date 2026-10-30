import logging

from data.repositories.settings import get_setting as rget_setting
from data.repositories.settings_definitions import get_setting_definitions
from shared.cache import CacheEntity
from shared.database import get_database
from shared.dto.setting import SettingItem
from shared.orm.setting import SettingModel
from shared.settings import get_setting as _get_setting
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .registry import get_cache_registry

logger = logging.getLogger(__name__)


def _settings_backend():
    return get_cache_registry().backend(CacheEntity.SETTINGS)


async def get_setting_cached(group: str, name: str, *, session: AsyncSession | None = None) -> SettingItem | None:
    backend = _settings_backend()
    cached = await backend.get(group, name, model=SettingItem, many=False)
    if cached:
        return cached

    if session:
        item = await rget_setting(session, group, name)
    else:
        item = await _get_setting(group, name)

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


async def create_default_settings() -> None:
    """Create default settings that are still missing.

    Existing rows are left untouched: settings are admin-managed,
    the seeder only fills the gaps. Idempotent.
    """
    definitions = get_setting_definitions()
    async with get_database().session_context() as session:
        for defn in definitions:
            result = await session.execute(
                select(SettingModel).where(
                    SettingModel.group == defn.group,
                    SettingModel.name == defn.name,
                ),
            )
            model = result.scalar_one_or_none()
            if model is not None:
                continue
            model = SettingModel(
                group=defn.group,
                name=defn.name,
                description=defn.description,
                value_type=defn.value_type,
                value=defn.default,
                locked=defn.locked,
            )
            session.add(model)
            await session.flush()
            item = SettingItem.from_model(model)
            await set_settings_cache(item)
            logger.info(
                "Created default setting: %s:%s = %s", defn.group, defn.name, defn.default
            )
