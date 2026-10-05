import datetime
from unittest.mock import patch

import pytest
from backend_user.services.route_link import (
    RouteLinkNotFoundError,
    get_route_by_link,
    parse_link_ids,
)
from module_shared.database import Database
from module_shared.schemas.container import ContainerType
from module_shared.schemas.route import ContainerOwner, RouteType

from .data import (
    CompanyFactory,
    ContainerFactory,
    DropFactory,
    PointFactory,
    PriceFactory,
    RouteFactory,
    ServiceFactory,
    ServicePriceFactory,
)


def test_parse_link_ids_ok():
    assert parse_link_ids("1,2,3") == [1, 2, 3]
    assert parse_link_ids(" 1 , 2 ") == [1, 2]
    assert parse_link_ids("5") == [5]


def test_parse_link_ids_empty():
    assert parse_link_ids(None) == []
    assert parse_link_ids("") == []


def test_parse_link_ids_invalid():
    with pytest.raises(RouteLinkNotFoundError):
        parse_link_ids("1,abc")


async def _seed_chained(session):
    company = CompanyFactory(name="LinkCo")
    point_a = PointFactory(city="A", RU_city="А")
    point_b = PointFactory(city="B", RU_city="Б")
    point_c = PointFactory(city="C", RU_city="В")
    point_d = PointFactory(city="D", RU_city="Г")
    container = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
    session.add_all([company, point_a, point_b, point_c, point_d, container])
    await session.flush()

    seg1 = RouteFactory(
        company_id=company.id,
        start_point_id=point_a.id,
        end_point_id=point_b.id,
        type=RouteType.RAIL,
        effective_to=datetime.datetime(2030, 1, 1),
    )
    seg2 = RouteFactory(
        company_id=company.id,
        start_point_id=point_b.id,
        end_point_id=point_c.id,
        type=RouteType.RAIL,
        effective_to=datetime.datetime(2030, 1, 1),
    )
    seg3 = RouteFactory(
        company_id=company.id,
        start_point_id=point_d.id,
        end_point_id=point_c.id,
        type=RouteType.RAIL,
        effective_to=datetime.datetime(2030, 1, 1),
    )
    session.add_all([seg1, seg2, seg3])
    await session.flush()

    for seg in (seg1, seg2, seg3):
        session.add(PriceFactory(route_id=seg.id, container_id=container.id))

    svc1 = ServiceFactory(name="Loading", internal_name="loading", mandatory=False, default=False)
    svc2 = ServiceFactory(name="Insurance", internal_name="insurance", mandatory=False, default=True)
    svc3 = ServiceFactory(name="Other", internal_name="other", mandatory=False, default=True)
    session.add_all([svc1, svc2, svc3])
    await session.flush()

    sp1 = ServicePriceFactory(route_id=seg1.id, service_id=svc1.id, currency="USD", price=10.0)
    sp2 = ServicePriceFactory(route_id=seg2.id, service_id=svc2.id, currency="USD", price=20.0)
    sp3 = ServicePriceFactory(route_id=seg3.id, service_id=svc3.id, currency="USD", price=30.0)
    session.add_all([sp1, sp2, sp3])
    await session.commit()
    return seg1, seg2, seg3, sp1, sp2, sp3


@pytest.mark.asyncio
async def test_get_route_by_link_ok(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, seg2, _seg3, sp1, sp2, _sp3 = await _seed_chained(session)

    with patch("backend_user.services.route_link.get_database", return_value=sqlite_db):
        route = await get_route_by_link([seg1.id, seg2.id], [sp1.id])

    assert [s.id for s in route.segments] == [seg1.id, seg2.id]
    assert route.drop is None
    assert route.may_be_invalid is False
    by_id = {s.id: s for s in route.services}
    assert by_id[sp1.id].checked is True
    assert by_id[sp2.id].checked is False


@pytest.mark.asyncio
async def test_get_route_by_link_no_services(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, _seg3, _sp1, _sp2, _sp3 = await _seed_chained(session)

    with patch("backend_user.services.route_link.get_database", return_value=sqlite_db):
        route = await get_route_by_link([seg1.id], [])

    assert len(route.segments) == 1
    assert all(s.checked is False for s in route.services)


@pytest.mark.asyncio
async def test_get_route_by_link_missing_segment(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, _seg3, _sp1, _sp2, _sp3 = await _seed_chained(session)

    with (
        patch("backend_user.services.route_link.get_database", return_value=sqlite_db),
        pytest.raises(RouteLinkNotFoundError),
    ):
        await get_route_by_link([seg1.id, 999999], [])


@pytest.mark.asyncio
async def test_get_route_by_link_broken_chain(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, seg3, _sp1, _sp2, _sp3 = await _seed_chained(session)

    with (
        patch("backend_user.services.route_link.get_database", return_value=sqlite_db),
        pytest.raises(RouteLinkNotFoundError),
    ):
        await get_route_by_link([seg1.id, seg3.id], [])


@pytest.mark.asyncio
async def test_get_route_by_link_foreign_service(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, seg2, _seg3, _sp1, _sp2, sp3 = await _seed_chained(session)

    with (
        patch("backend_user.services.route_link.get_database", return_value=sqlite_db),
        pytest.raises(RouteLinkNotFoundError),
    ):
        await get_route_by_link([seg1.id, seg2.id], [sp3.id])


@pytest.mark.asyncio
async def test_get_route_by_link_missing_service(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, _seg3, _sp1, _sp2, _sp3 = await _seed_chained(session)

    with (
        patch("backend_user.services.route_link.get_database", return_value=sqlite_db),
        pytest.raises(RouteLinkNotFoundError),
    ):
        await get_route_by_link([seg1.id], [999999])


@pytest.mark.asyncio
async def test_get_route_by_link_duplicates(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, _seg3, _sp1, _sp2, _sp3 = await _seed_chained(session)

    with patch("backend_user.services.route_link.get_database", return_value=sqlite_db):
        with pytest.raises(RouteLinkNotFoundError):
            await get_route_by_link([seg1.id, seg1.id], [])
        with pytest.raises(RouteLinkNotFoundError):
            await get_route_by_link([], [])


@pytest.mark.asyncio
async def test_get_route_by_link_mandatory_checked(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="LinkCo2")
        point_a = PointFactory(city="A2", RU_city="А2")
        point_b = PointFactory(city="B2", RU_city="Б2")
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
        session.add_all([company, point_a, point_b, container])
        await session.flush()

        seg = RouteFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            effective_to=datetime.datetime(2030, 1, 1),
        )
        session.add(seg)
        await session.flush()
        session.add(PriceFactory(route_id=seg.id, container_id=container.id))

        svc = ServiceFactory(name="Mandatory", internal_name="mandatory", mandatory=True, default=False)
        session.add(svc)
        await session.flush()
        sp = ServicePriceFactory(route_id=seg.id, service_id=svc.id, currency="USD", price=5.0)
        session.add(sp)
        await session.commit()

    with patch("backend_user.services.route_link.get_database", return_value=sqlite_db):
        route = await get_route_by_link([seg.id], [])

    assert len(route.services) == 1
    assert route.services[0].mandatory is True
    assert route.services[0].checked is True


@pytest.mark.asyncio
async def test_get_route_by_link_sea_rail_drop(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="SeaRailCo")
        point_a = PointFactory(city="SA", RU_city="СА")
        point_drop = PointFactory(city="SD", RU_city="СД")
        point_b = PointFactory(city="SB", RU_city="СБ")
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
        session.add_all([company, point_a, point_drop, point_b, container])
        await session.flush()

        sea = RouteFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_drop.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
            effective_to=datetime.datetime(2030, 1, 1),
        )
        rail = RouteFactory(
            company_id=company.id,
            start_point_id=point_drop.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
            is_through=False,
            effective_to=datetime.datetime(2030, 1, 1),
        )
        session.add_all([sea, rail])
        await session.flush()
        session.add_all([
            PriceFactory(route_id=sea.id, container_id=container.id),
            PriceFactory(route_id=rail.id, container_id=container.id),
        ])
        session.add(DropFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=point_drop.id,
            end_point_id=point_b.id,
            price=500.0,
            currency="USD",
        ))
        await session.commit()

    with patch("backend_user.services.route_link.get_database", return_value=sqlite_db):
        route = await get_route_by_link([sea.id, rail.id], [])

    assert [s.type for s in route.segments] == ["SEA", "RAIL"]
    assert route.drop is not None
    assert route.drop.price == 500.0


@pytest.mark.asyncio
async def test_get_route_by_link_expired(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, _seg3, _sp1, _sp2, _sp3 = await _seed_chained(session)
        seg1.effective_to = datetime.datetime(2020, 1, 1)
        session.add(seg1)
        await session.commit()

    with patch("backend_user.services.route_link.get_database", return_value=sqlite_db):
        route = await get_route_by_link([seg1.id], [])

    assert route.may_be_invalid is True
