from shared.dto.errors import NotFoundError, ValidationError
from shared.orm.demo_guest import DemoGuestModel
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


async def create_demo_guest(
    session: AsyncSession,
    uid: str,
    sea_profit,
    sea_profit_currency: str,
    rail_profit,
    rail_profit_currency: str,
) -> DemoGuestModel:
    if await get_demo_guest_by_uid(session, uid):
        raise ValidationError("UID already exists")
    guest = DemoGuestModel(
        uid=uid,
        sea_profit=sea_profit,
        sea_profit_currency=sea_profit_currency,
        rail_profit=rail_profit,
        rail_profit_currency=rail_profit_currency,
    )
    session.add(guest)
    await session.flush()
    await session.refresh(guest)
    return guest


async def update_demo_guest(
    session: AsyncSession,
    guest_id: int,
    uid: str,
    sea_profit,
    sea_profit_currency: str,
    rail_profit,
    rail_profit_currency: str,
) -> DemoGuestModel:
    guest = await session.get(DemoGuestModel, guest_id)
    if not guest:
        raise NotFoundError("Demo guest not found")
    existing = await get_demo_guest_by_uid(session, uid)
    if existing and existing.id != guest_id:
        raise ValidationError("UID already exists")
    guest.uid = uid
    guest.sea_profit = sea_profit
    guest.sea_profit_currency = sea_profit_currency
    guest.rail_profit = rail_profit
    guest.rail_profit_currency = rail_profit_currency
    await session.flush()
    await session.refresh(guest)
    return guest


async def delete_demo_guest(session: AsyncSession, guest_id: int) -> None:
    guest = await session.get(DemoGuestModel, guest_id)
    if not guest:
        raise NotFoundError("Demo guest not found")
    await session.delete(guest)
