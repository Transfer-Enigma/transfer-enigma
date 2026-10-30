"""Settings seed service.

Creates default settings that are still missing.
"""

import logging

from data.setings.cached import set_settings_cache
from shared.database import get_database
from shared.models.setting import SettingItem, parse_setting_value
from shared.orm.setting import SettingModel
from shared.setting_definitions import get_setting_definitions
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def do_seed() -> None:
    """Create missing default settings."""
    await ensure_settings()


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
