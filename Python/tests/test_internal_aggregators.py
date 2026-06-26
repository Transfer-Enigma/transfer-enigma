import datetime
from unittest.mock import patch

import pytest
from module_data_internal.aggregators.containers import get_containers, search_container_ids
from module_data_internal.aggregators.routes import find_all_paths, process_results
from module_data_internal.schemas import ContainerOwner, ContainerType, RouteType
from module_shared.database import Database
from module_shared.models.route import ContainerItem
from module_shared.models.setting import SettingItem
from module_shared.schemas.setting import SettingType

from .data import (
    CompanyFactory,
    ContainerFactory,
    DropOffFactory,
    PointFactory,
    PriceFactory,
    RouteSegmentFactory,
    ServiceFactory,
    ServicePriceFactory,
)


def _seed_id_counter():
    counter = 0
    while True:
        counter += 1
        yield counter


_id_counter = _seed_id_counter()


def _unique_point(**kwargs) -> dict:
    n = next(_id_counter)
    overrides = {
        "city": f"City{n}",
        "country": f"CO{n}",
        "RU_city": f"Город{n}",
        "RU_country": f"Страна{n}",
    }
    overrides.update(kwargs)
    return overrides


async def _seed_basic_data(session):
    company = CompanyFactory(name="TestRailCo")
    point_a = PointFactory(**_unique_point())
    point_b = PointFactory(**_unique_point())
    container = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)

    session.add_all([company, point_a, point_b, container])
    await session.flush()
    return company, point_a, point_b, container


@pytest.mark.asyncio
async def test_get_containers(sqlite_db: Database):
    c1 = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
    c2 = ContainerFactory(size=40, weight_from=0, weight_to=28000, name="40DC", type=ContainerType.DC)

    async with sqlite_db.session_context() as session:
        session.add_all([c1, c2])
        await session.commit()

    with patch("module_data_internal.aggregators.containers.get_database", return_value=sqlite_db):
        result = await get_containers(datetime.date(2024, 6, 15), "1", "2")

    result_list = list(result)
    assert len(result_list) == 2
    sizes = {c.size for c in result_list}
    assert sizes == {20, 40}


def test_search_container_ids_edge():
    containers = [
        ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC),
        ContainerItem(id=2, size=20, weight_from=28001, weight_to=50000, name="20DC", type=ContainerType.DC),
        ContainerItem(id=3, size=40, weight_from=0, weight_to=28000, name="40DC", type=ContainerType.DC),
        ContainerItem(id=4, size=40, weight_from=28001, weight_to=50000, name="40DC", type=ContainerType.DC),
    ]

    assert search_container_ids(containers, weight=0, size=20) == [1]
    assert search_container_ids(containers, weight=28000, size=20) == [1]
    assert search_container_ids(containers, weight=28001, size=20) == [2]
    assert search_container_ids(containers, weight=50000, size=40) == [4]
    assert search_container_ids(containers, weight=50001, size=40) == []
    assert search_container_ids(containers, weight=20000, size=30) == []
    assert search_container_ids(containers, weight=-1, size=20) == []


def test_search_container_ids():
    containers = [
        ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC),
        ContainerItem(id=2, size=20, weight_from=28001, weight_to=50000, name="20DC", type=ContainerType.DC),
        ContainerItem(id=3, size=40, weight_from=0, weight_to=28000, name="40DC", type=ContainerType.DC),
    ]

    assert search_container_ids(containers, weight=20000, size=20) == [1]
    assert search_container_ids(containers, weight=30000, size=20) == [2]
    assert search_container_ids(containers, weight=20000, size=40) == [3]
    assert search_container_ids(containers, weight=100000, size=20) == []


@pytest.mark.asyncio
async def test_find_all_paths_rail(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        route_model = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
        )
        session.add(route_model)
        await session.flush()

        price = PriceFactory(route_id=route_model.id, container_id=container.id)
        session.add(price)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) == 1
    route = routes[0]
    assert len(route.segments) == 1
    assert route.segments[0].type == "RAIL"
    assert route.segments[0].company == "TestRailCo"


@pytest.mark.asyncio
async def test_find_all_paths_sea(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.SEA,
        )
        session.add(route)
        await session.flush()

        price = PriceFactory(route_id=route.id, container_id=container.id)
        session.add(price)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) == 1
    assert routes[0].segments[0].type == "SEA"


@pytest.mark.asyncio
async def test_find_all_paths_sea_rail_same_company_coc(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        drop_point = PointFactory(**_unique_point())
        session.add(drop_point)
        await session.flush()

        sea_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=drop_point.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        session.add_all([sea_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
        )
        session.add(drop)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) >= 1
    result_route = routes[0]
    assert len(result_route.segments) == 2
    assert result_route.segments[0].type == "SEA"
    assert result_route.segments[1].type == "RAIL"


@pytest.mark.asyncio
async def test_find_all_paths_expired_route(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            effective_from=datetime.date(2023, 1, 1),
            effective_to=datetime.date(2023, 12, 31),
        )
        session.add(route)
        await session.flush()

        price = PriceFactory(route_id=route.id, container_id=container.id)
        session.add(price)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) == 0


@pytest.mark.asyncio
async def test_find_all_paths_no_matching_container(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
        )
        session.add(route)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[999],
        )

    routes = list(result)
    assert len(routes) == 0


@pytest.mark.asyncio
async def test_find_all_paths_sea_rail_different_company_soc(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company_a = CompanyFactory(name="SeaCo")
        company_b = CompanyFactory(name="RailCo")
        point_a = PointFactory(**_unique_point())
        point_mid = PointFactory(**_unique_point())
        point_b = PointFactory(**_unique_point())
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
        session.add_all([company_a, company_b, point_a, point_mid, point_b, container])
        await session.flush()

        sea_route = RouteSegmentFactory(
            company_id=company_a.id,
            start_point_id=point_a.id,
            end_point_id=point_mid.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company_b.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.SOC,
            is_through=False,
        )
        session.add_all([sea_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company_a.id,
            container_id=container.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
        )
        session.add(drop)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) >= 1
    route = routes[0]
    assert len(route.segments) == 2
    assert route.segments[0].type == "SEA"
    assert route.segments[0].company == "SeaCo"
    assert route.segments[1].type == "RAIL"
    assert route.segments[1].company == "RailCo"


@pytest.mark.asyncio
async def test_find_all_paths_sea_rail_same_company_soc(sqlite_db: Database):
    """Check regressions of bug#135"""
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        point_mid = PointFactory(**_unique_point())
        session.add(point_mid)
        await session.flush()

        sea_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_mid.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.SOC,
            is_through=False,
        )
        session.add_all([sea_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
        )
        session.add(drop)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) >= 1
    result_route = routes[0]
    assert len(result_route.segments) == 2
    assert result_route.segments[0].type == "SEA"
    assert result_route.segments[1].type == "RAIL"
    assert result_route.segments[1].container_owner == "SOC"


@pytest.mark.asyncio
async def test_find_all_paths_no_data(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        await _seed_basic_data(session)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=999,
            end_point_id=998,
            container_ids=[999],
        )

    routes = list(result)
    assert len(routes) == 0


@pytest.mark.asyncio
async def test_find_all_paths_sea_rail_with_drop_price(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="DropCo")
        point_a = PointFactory(**_unique_point())
        point_mid = PointFactory(**_unique_point())
        point_b = PointFactory(**_unique_point())
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000)
        session.add_all([company, point_a, point_mid, point_b, container])
        await session.flush()

        sea_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_mid.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        session.add_all([sea_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
            price=999.0,
        )
        session.add(drop)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) >= 1
    route = routes[0]
    assert route.drop is not None
    assert route.drop.price == 999.0


@pytest.mark.asyncio
async def test_find_all_paths_with_dropp_off_point(sqlite_db: Database):
    """Sea route has a dropp_off_point_id set. The sea+rail join requires
    SeaRoute.dropp_off_point_id == RailRoute.end_point_id, so the rail route
    must end at the drop-off point."""
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="DroppCo")
        point_a = PointFactory(**_unique_point())
        point_mid = PointFactory(**_unique_point())
        point_dropp = PointFactory(**_unique_point())
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000)
        session.add_all([company, point_a, point_mid, point_dropp, container])
        await session.flush()

        sea_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_mid.id,
            dropp_off_point_id=point_dropp.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_mid.id,
            end_point_id=point_dropp.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
        )
        session.add_all([sea_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_dropp.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) >= 1
    route = routes[0]
    assert len(route.segments) == 2
    assert route.segments[0].type == "SEA"
    assert route.segments[1].type == "RAIL"


@pytest.mark.asyncio
async def test_find_all_paths_with_services(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        route_model = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
        )
        session.add(route_model)
        await session.flush()

        price = PriceFactory(route_id=route_model.id, container_id=container.id)
        session.add(price)
        await session.flush()

        service = ServiceFactory()
        session.add(service)
        await session.flush()

        sp = ServicePriceFactory(
            route_id=route_model.id,
            service_id=service.id,
            container_id=None,
        )
        session.add(sp)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) == 1
    route = routes[0]
    assert len(route.services) == 1
    assert route.services[0].name == "Test Service"


def test_process_results_skips_exception():
    result = process_results(
        [ValueError("db error")],
        datetime.date(2024, 6, 15),
        [1],
    )
    assert result == []


def test_process_results_skips_empty():
    result = process_results(
        [[], None, Exception()],
        datetime.date(2024, 6, 15),
        [1],
    )
    assert result == []


@pytest.mark.asyncio
async def test_find_all_paths_sea_rail_drop_valid_on_shipping_date(sqlite_db: Database):
    """Check regressions of bug#131"""
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="DropDateCo")
        point_a = PointFactory(**_unique_point())
        point_mid = PointFactory(**_unique_point())
        point_b = PointFactory(**_unique_point())
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000)
        session.add_all([company, point_a, point_mid, point_b, container])
        await session.flush()

        sea_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_mid.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        session.add_all([sea_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
            effective_from=datetime.date(2024, 6, 1),
            effective_to=datetime.date(2024, 6, 30),
            price=50.0,
        )
        session.add(drop)
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    assert len(routes) >= 1
    route = routes[0]
    assert route.drop is not None
    assert route.drop.price == 50.0


@pytest.mark.asyncio
async def test_find_all_paths_sea_rail_no_drop_filtered_out(sqlite_db: Database):
    """Check regressions of bug#132"""
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="NoDropCo")
        point_a = PointFactory(**_unique_point())
        point_mid = PointFactory(**_unique_point())
        point_b = PointFactory(**_unique_point())
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000)
        session.add_all([company, point_a, point_mid, point_b, container])
        await session.flush()

        sea_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_mid.id,
            dropp_off_point_id=None,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_mid.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        session.add_all([sea_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    sea_rail_routes = [r for r in routes if len(r.segments) == 2]
    assert len(sea_rail_routes) == 0


@pytest.mark.asyncio
async def test_find_all_paths_sea_soc_shown_when_flag_off(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        drop_point = PointFactory(**_unique_point())
        session.add(drop_point)
        await session.flush()

        sea_soc_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=drop_point.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.SOC,
            is_through=False,
        )
        sea_coc_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=drop_point.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        session.add_all([sea_soc_route, sea_coc_route, rail_route])
        await session.flush()

        price_sea_soc = PriceFactory(route_id=sea_soc_route.id, container_id=container.id)
        price_sea_coc = PriceFactory(route_id=sea_coc_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea_soc, price_sea_coc, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
        )
        session.add(drop)
        await session.commit()

    setting = SettingItem(
        group="feature-flag", name="hide-sea-soc",
        value_type=SettingType.BOOL, value=False,
    )

    with (
        patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db),
        patch("module_data_internal.aggregators.routes.get_setting_cached", return_value=setting),
    ):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    sea_rail_routes = [r for r in routes if len(r.segments) == 2]
    assert len(sea_rail_routes) == 2
    sea_owners = {r.segments[0].container_owner for r in sea_rail_routes}
    assert sea_owners == {"SOC", "COC"}


@pytest.mark.asyncio
async def test_find_all_paths_sea_soc_default_when_setting_missing(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        drop_point = PointFactory(**_unique_point())
        session.add(drop_point)
        await session.flush()

        sea_soc_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=drop_point.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.SOC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.COC,
            is_through=False,
        )
        session.add_all([sea_soc_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_soc_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
        )
        session.add(drop)
        await session.commit()

    with (
        patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db),
        patch("module_data_internal.aggregators.routes.get_setting_cached", return_value=None),
    ):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    sea_rail_routes = [r for r in routes if len(r.segments) == 2]
    assert len(sea_rail_routes) == 1
    assert sea_rail_routes[0].segments[0].container_owner == "SOC"


@pytest.mark.asyncio
async def test_find_all_paths_sea_soc_hidden_by_flag(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company, point_a, point_b, container = await _seed_basic_data(session)

        drop_point = PointFactory(**_unique_point())
        session.add(drop_point)
        await session.flush()

        sea_soc_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=drop_point.id,
            type=RouteType.SEA,
            container_owner=ContainerOwner.SOC,
            is_through=False,
        )
        rail_route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            container_owner=ContainerOwner.SOC,
            is_through=False,
        )
        session.add_all([sea_soc_route, rail_route])
        await session.flush()

        price_sea = PriceFactory(route_id=sea_soc_route.id, container_id=container.id)
        price_rail = PriceFactory(route_id=rail_route.id, container_id=container.id)
        session.add_all([price_sea, price_rail])
        await session.flush()

        drop = DropOffFactory(
            company_id=company.id,
            container_id=container.id,
            start_point_id=drop_point.id,
            end_point_id=point_b.id,
        )
        session.add(drop)
        await session.commit()

    setting = SettingItem(
        group="feature-flag", name="hide-sea-soc",
        value_type=SettingType.BOOL, value=True,
    )

    with (
        patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db),
        patch("module_data_internal.aggregators.routes.get_setting_cached", return_value=setting),
    ):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    routes = list(result)
    sea_rail_routes = [r for r in routes if len(r.segments) == 2]
    assert len(sea_rail_routes) == 0
