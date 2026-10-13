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


async def list_settings(session: AsyncSession, group: str | None = None) -> list[SettingItem]:
    stmt = select(SettingModel).order_by(SettingModel.group, SettingModel.name)
    if group is not None:
        stmt = stmt.where(SettingModel.group == group)
    result = await session.execute(stmt)
    return [SettingItem.from_model(m) for m in result.scalars().all()]
