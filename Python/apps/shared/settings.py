from shared.models.setting import SettingItem

from .database import get_database
from .repositories.setting import get_setting as rget_setting


async def get_setting(group: str, name: str) -> SettingItem | None:
    async with get_database().session_context() as session:
        return await rget_setting(session, group, name)
