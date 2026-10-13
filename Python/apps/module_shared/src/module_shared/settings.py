from .database import get_database
from .models.setting import SettingItem
from .repositories.setting import get_setting as rget_setting
from .repositories.setting import list_settings as rlist_settings


async def get_setting(group: str, name: str) -> SettingItem | None:
    async with get_database().session_context() as session:
        return await rget_setting(session, group, name)


async def list_settings(group: str | None = None) -> list[SettingItem]:
    async with get_database().session_context() as session:
        return await rlist_settings(session, group)
