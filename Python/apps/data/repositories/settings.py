from shared.database import get_database
from shared.dto.setting import SettingItem
from shared.orm.setting import SettingModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_setting(session: AsyncSession, group: str, name: str) -> SettingItem | None:
    """The setting of the group, or None when it does not exist."""
    result = await session.execute(
        select(SettingModel).where(
            SettingModel.group == group,
            SettingModel.name == name,
        ),
    )
    model = result.scalar_one_or_none()
    return SettingItem.from_model(model) if model else None


async def load_setting(group: str, name: str) -> SettingItem | None:
    """The setting of the group, read with a session of its own."""
    async with get_database().session_context() as session:
        return await get_setting(session, group, name)
