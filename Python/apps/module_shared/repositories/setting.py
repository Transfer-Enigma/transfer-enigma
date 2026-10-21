from module_shared.models.setting import SettingItem
from module_shared.schemas.setting import SettingModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_setting(session: AsyncSession, group: str, name: str) -> SettingItem | None:
    result = await session.execute(
        select(SettingModel).where(
            SettingModel.group == group,
            SettingModel.name == name,
        ),
    )
    model = result.scalar_one_or_none()
    return SettingItem.from_model(model) if model else None
