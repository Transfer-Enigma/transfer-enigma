from module_shared.schemas.demo_guest import DemoGuestModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_demo_guest_by_uid(session: AsyncSession, uid: str) -> DemoGuestModel | None:
    result = await session.execute(
        select(DemoGuestModel).where(DemoGuestModel.uid == uid),
    )
    return result.scalar_one_or_none()


async def list_demo_guests(session: AsyncSession) -> list[DemoGuestModel]:
    result = await session.execute(
        select(DemoGuestModel).order_by(DemoGuestModel.uid),
    )
    return list(result.scalars().all())
