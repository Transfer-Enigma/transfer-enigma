import logging
from functools import cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .cache import CacheController
from .database import get_database
from .models.setting import SettingItem, parse_setting_value
from .redis_client import get_redis
from .repositories import setting as rsettings
from .schemas.setting import SettingModel
from .setting_definitions import get_setting_definitions
from .settings import get_setting as _get_setting

logger = logging.getLogger(__name__)

SETTINGS_CACHE_TTL = 43200  # 12 hours
SETTINGS_CACHE_PREFIX = "backend_user:settings"


@cache
def get_cache_controller():
    return CacheController(logger)


def _settings_cache_key(group: str, name: str) -> str:
    return f"{SETTINGS_CACHE_PREFIX}:{group}:{name}"


async def get_setting_cached(group: str, name: str, *, session: AsyncSession | None = None) -> SettingItem | None:
    key = _settings_cache_key(group, name)
    cache_controller = get_cache_controller()
    cached = await cache_controller.get_cached(key, SettingItem, False)
    if cached:
        return cached

    if session:
        item = await rsettings.get_setting(session, group, name)
    else:
        item = await _get_setting(group, name)

    if item is not None:
        cache_controller.silent_set_cache_async(key, item, SETTINGS_CACHE_TTL)

    return item


async def set_settings_cache(item: SettingItem) -> None:
    key = _settings_cache_key(item.group, item.name)
    cache_controller = get_cache_controller()
    await cache_controller.set_cache(key, item, SETTINGS_CACHE_TTL, True)


async def delete_settings_cache(group: str, name: str) -> None:
    key = _settings_cache_key(group, name)
    try:
        redis = get_redis()
        await redis.delete(key)
        logger.debug("Settings cache deleted: %s", key)
    except Exception:
        logger.exception("Failed to delete settings cache: %s", key)


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
