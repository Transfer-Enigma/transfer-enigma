import datetime
from unittest.mock import patch

import pytest
from module_data_internal.aggregators.points import (
    get_departure_points,
    get_destination_points,
    get_truck_departure_points,
    get_truck_destination_points,
)
from module_shared.database import Database
from module_shared.schemas.route import RouteType

from .data import CompanyFactory, PointFactory, RouteFactory


def _unique_point(prefix: str, counter: list) -> dict:
    counter[0] += 1
    n = counter[0]
    return {
        "city": f"City{n}",
        "country": f"CO{n}",
        "RU_city": f"Город{n}_{prefix}",
        "RU_country": f"Страна{n}_{prefix}",
    }


@pytest.mark.asyncio
async def test_get_departure_points(sqlite_db: Database):
    counter = [0]
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="PointCo")
        point_a = PointFactory(**_unique_point("dep", counter))
        point_b = PointFactory(**_unique_point("dep", counter))
        session.add_all([company, point_a, point_b])
        await session.flush()

        effective_to = datetime.date(2025, 12, 31)
        route = RouteFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            effective_from=datetime.date(2024, 1, 1),
            effective_to=effective_to,
        )
        session.add(route)
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        results = await get_departure_points(date=effective_to)

    assert len(results) >= 1
    point_model, company_model = results[0]
    assert point_model.id == point_a.id
    assert company_model.id == company.id


@pytest.mark.asyncio
async def test_get_destination_points(sqlite_db: Database):
    counter = [0]
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="DestCo")
        point_a = PointFactory(**_unique_point("dest", counter))
        point_b = PointFactory(**_unique_point("dest", counter))
        session.add_all([company, point_a, point_b])
        await session.flush()

        effective_to = datetime.date(2025, 12, 31)
        route = RouteFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.RAIL,
            effective_from=datetime.date(2024, 1, 1),
            effective_to=effective_to,
        )
        session.add(route)
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        results = await get_destination_points(date=effective_to)

    assert len(results) >= 1
    point_model, company_model = results[0]
    assert point_model.id == point_b.id
    assert company_model.id == company.id


@pytest.mark.asyncio
async def test_get_points_no_routes(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="Orphan")
        point = PointFactory()
        session.add_all([company, point])
        await session.commit()

    date = datetime.date(2025, 12, 31)
    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        dep_results = await get_departure_points(date=date)
        dest_results = await get_destination_points(date=date)

    assert len(dep_results) == 0
    assert len(dest_results) == 0


@pytest.mark.asyncio
async def test_get_points_multiple_companies(sqlite_db: Database):
    counter = [0]
    async with sqlite_db.session_context() as session:
        company_a = CompanyFactory(name="Alpha")
        company_b = CompanyFactory(name="Beta")
        point_a = PointFactory(**_unique_point("multi", counter))
        point_b = PointFactory(**_unique_point("multi", counter))
        session.add_all([company_a, company_b, point_a, point_b])
        await session.flush()

        route_a = RouteFactory(
            company_id=company_a.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.SEA,
        )
        route_b = RouteFactory(
            company_id=company_b.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteType.SEA,
        )
        session.add_all([route_a, route_b])
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        dep_results = await get_departure_points(date=datetime.date(2025, 12, 31))

    assert len(dep_results) == 2
    company_names = {c.name for _, c in dep_results}
    assert company_names == {"Alpha", "Beta"}


@pytest.mark.asyncio
async def test_truck_routes_excluded_from_departures(sqlite_db: Database):
    counter = [0]
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="TruckCo")
        point_door = PointFactory(**_unique_point("truck_excl", counter))
        point_port = PointFactory(**_unique_point("truck_excl", counter))
        session.add_all([company, point_door, point_port])
        await session.flush()

        truck_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_door.id,
            end_point_id=point_port.id,
            type=RouteType.TRUCK,
        )
        rail_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_port.id,
            end_point_id=point_door.id,
            type=RouteType.RAIL,
        )
        session.add_all([truck_route, rail_route])
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        dep_results = await get_departure_points(date=datetime.date(2025, 12, 31))

    dep_point_ids = [p.id for p, _ in dep_results]
    assert point_port.id in dep_point_ids
    assert point_door.id not in dep_point_ids


@pytest.mark.asyncio
async def test_truck_routes_excluded_from_destinations(sqlite_db: Database):
    counter = [0]
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="TruckCo")
        point_door = PointFactory(**_unique_point("truck_excl_d", counter))
        point_port = PointFactory(**_unique_point("truck_excl_d", counter))
        session.add_all([company, point_door, point_port])
        await session.flush()

        truck_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_door.id,
            end_point_id=point_port.id,
            type=RouteType.TRUCK,
        )
        rail_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_port.id,
            end_point_id=point_door.id,
            type=RouteType.RAIL,
        )
        session.add_all([truck_route, rail_route])
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        dest_results = await get_destination_points(date=datetime.date(2025, 12, 31))

    dest_point_ids = [p.id for p, _ in dest_results]
    assert point_door.id in dest_point_ids
    assert point_port.id not in dest_point_ids


@pytest.mark.asyncio
async def test_get_truck_departure_points(sqlite_db: Database):
    counter = [0]
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="TruckCo")
        point_door = PointFactory(**_unique_point("truck_dep", counter))
        point_port = PointFactory(**_unique_point("truck_dep", counter))
        session.add_all([company, point_door, point_port])
        await session.flush()

        truck_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_door.id,
            end_point_id=point_port.id,
            type=RouteType.TRUCK,
        )
        rail_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_port.id,
            end_point_id=point_door.id,
            type=RouteType.RAIL,
        )
        session.add_all([truck_route, rail_route])
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        results = await get_truck_departure_points(date=datetime.date(2025, 12, 31))

    point_ids = [p.id for p, _ in results]
    assert point_door.id in point_ids
    assert point_port.id not in point_ids


@pytest.mark.asyncio
async def test_get_truck_destination_points(sqlite_db: Database):
    counter = [0]
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="TruckCo")
        point_door = PointFactory(**_unique_point("truck_dest", counter))
        point_port = PointFactory(**_unique_point("truck_dest", counter))
        session.add_all([company, point_door, point_port])
        await session.flush()

        truck_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_door.id,
            end_point_id=point_port.id,
            type=RouteType.TRUCK,
        )
        rail_route = RouteFactory(
            company_id=company.id,
            start_point_id=point_port.id,
            end_point_id=point_door.id,
            type=RouteType.RAIL,
        )
        session.add_all([truck_route, rail_route])
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        results = await get_truck_destination_points(date=datetime.date(2025, 12, 31))

    point_ids = [p.id for p, _ in results]
    assert point_port.id in point_ids
    assert point_door.id not in point_ids
