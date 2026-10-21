import logging

from shared.cache import CacheEntity
from shared.database import get_database
from shared.dto.setting import SettingItem, parse_setting_value
from shared.orm.setting import SettingModel
from shared.repositories import setting as rsettings
from shared.setting_definitions import get_setting_definitions
from shared.settings import get_setting as _get_setting
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

<<<<<<<< HEAD:Python/apps/data/cache/settings.py
from .registry import get_cache_registry
========
from .cache_controller import CacheController
from .database import get_database
from .models.setting import SettingItem, parse_setting_value
from .redis_client import get_redis
from .repositories import setting as rsettings
from .schemas.setting import SettingModel
from .setting_definitions import get_setting_definitions
from .settings import get_setting as _get_setting
>>>>>>>> a90e866f (Python: Rename packages by architecture layer):Python/apps/shared/cache_settings.py

logger = logging.getLogger(__name__)


def _settings_backend():
    return get_cache_registry().backend(CacheEntity.SETTINGS)


async def get_setting_cached(group: str, name: str, *, session: AsyncSession | None = None) -> SettingItem | None:
    backend = _settings_backend()
    cached = await backend.get(group, name, model=SettingItem, many=False)
    if cached:
        return cached

    if session:
        item = await rsettings.get_setting(session, group, name)
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


async def ensure_settings() -> None:
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
                await _sync_locked(session, model, defn)
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
            logger.info("Created default setting: %s:%s = %s", defn.group, defn.name, defn.default)


async def _sync_locked(session, model, defn) -> None:
    changed = False
    if not model.locked and defn.locked:
        model.locked = True
        changed = True
    if model.value_type != defn.value_type:
        logger.warning(
            "Syncing value_type for %s:%s: %s -> %s",
            defn.group, defn.name, model.value_type, defn.value_type,
        )
        model.value_type = defn.value_type
        changed = True
    if model.value is None and defn.default is not None:
        try:
            parse_setting_value(defn.default, model.value_type)
            model.value = defn.default
            changed = True
        except (ValueError, TypeError):
            logger.warning("Cannot convert default for %s:%s", defn.group, defn.name)
    if changed:
        await session.flush()
        item = SettingItem.from_model(model)
        await set_settings_cache(item)
