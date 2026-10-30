from shared.database import get_database
from shared.models.setting import SettingItem
from shared.orm.setting import SettingModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_setting_with_session(session: AsyncSession, group: str, name: str) -> SettingItem | None:
    result = await session.execute(
        select(SettingModel).where(
            SettingModel.group == group,
            SettingModel.name == name,
        ),
    )
    model = result.scalar_one_or_none()
    return SettingItem.from_model(model) if model else None


async def get_setting(group: str, name: str) -> SettingItem | None:
    async with get_database().session_context() as session:
        return await get_setting_with_session(session, group, name)
