from decimal import Decimal

import pytest
<<<<<<< HEAD
from shared.orm.demo_guest import DemoGuestModel
from shared.repositories.demo_guest import get_demo_guest_by_uid, list_demo_guests
=======
from shared.repositories.demo_guest import get_demo_guest_by_uid, list_demo_guests
from shared.schemas.demo_guest import DemoGuestModel
>>>>>>> a90e866f (Python: Rename packages by architecture layer)


@pytest.mark.asyncio
async def test_get_demo_guest_by_uid_found(sqlite_session):
    guest = DemoGuestModel(uid="test-uid", sea_profit=Decimal("10"), rail_profit=Decimal("20"))
    sqlite_session.add(guest)
    await sqlite_session.commit()

    result = await get_demo_guest_by_uid(sqlite_session, "test-uid")
    assert result is not None
    assert result.uid == "test-uid"
    assert float(result.sea_profit) == 10.0
    assert float(result.rail_profit) == 20.0


@pytest.mark.asyncio
async def test_get_demo_guest_by_uid_not_found(sqlite_session):
    result = await get_demo_guest_by_uid(sqlite_session, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_demo_guests_empty(sqlite_session):
    result = await list_demo_guests(sqlite_session)
    assert result == []


@pytest.mark.asyncio
async def test_list_demo_guests_multiple(sqlite_session):
    guests = [
        DemoGuestModel(uid="z-uid", sea_profit=Decimal("0"), rail_profit=Decimal("0")),
        DemoGuestModel(uid="a-uid", sea_profit=Decimal("5"), rail_profit=Decimal("5")),
        DemoGuestModel(uid="m-uid", sea_profit=Decimal("10"), rail_profit=Decimal("10")),
    ]
    for g in guests:
        sqlite_session.add(g)
    await sqlite_session.commit()

    result = await list_demo_guests(sqlite_session)
    assert len(result) == 3
    assert [r.uid for r in result] == ["a-uid", "m-uid", "z-uid"]


@pytest.mark.asyncio
async def test_get_demo_guest_by_uid_with_profit_overrides(sqlite_session):
    guest = DemoGuestModel(
        uid="profit-uid",
        sea_profit=Decimal("150.50"),
        sea_profit_currency="EUR",
        rail_profit=Decimal("75.25"),
        rail_profit_currency="USD",
    )
    sqlite_session.add(guest)
    await sqlite_session.commit()

    result = await get_demo_guest_by_uid(sqlite_session, "profit-uid")
    assert result is not None
    assert float(result.sea_profit) == 150.50
    assert result.sea_profit_currency == "EUR"
    assert float(result.rail_profit) == 75.25
    assert result.rail_profit_currency == "USD"
