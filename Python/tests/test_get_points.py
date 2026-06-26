import datetime
from unittest.mock import patch

import pytest
from module_data_internal.aggregators.points import get_departure_points, get_destination_points
from module_data_internal.schemas import RouteSegmentType
from module_shared.database import Database

from .data import CompanyFactory, PointFactory, RouteSegmentFactory


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

        route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteSegmentType.RAIL,
            effective_from=datetime.date(2024, 1, 1),
            effective_to=datetime.date(2025, 12, 31),
        )
        session.add(route)
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        results = await get_departure_points()

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

        route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteSegmentType.RAIL,
            effective_from=datetime.date(2024, 1, 1),
            effective_to=datetime.date(2025, 12, 31),
        )
        session.add(route)
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        results = await get_destination_points()

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

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        dep_results = await get_departure_points()
        dest_results = await get_destination_points()

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

        route_a = RouteSegmentFactory(
            company_id=company_a.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteSegmentType.SEA,
        )
        route_b = RouteSegmentFactory(
            company_id=company_b.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteSegmentType.SEA,
        )
        session.add_all([route_a, route_b])
        await session.commit()

    with patch("module_data_internal.aggregators.points.get_database", return_value=sqlite_db):
        dep_results = await get_departure_points()

    assert len(dep_results) == 2
    company_names = {c.name for _, c in dep_results}
    assert company_names == {"Alpha", "Beta"}
