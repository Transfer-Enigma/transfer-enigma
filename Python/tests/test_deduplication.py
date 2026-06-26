import datetime
from unittest.mock import patch

import pytest
from module_data_internal.aggregators.routes import find_all_paths
from module_data_internal.schemas import ContainerOwner, ContainerType, RouteSegmentType
from module_shared.database import Database

from .data import CompanyFactory, ContainerFactory, PointFactory, PriceFactory, RouteSegmentFactory


def _id_counter():
    n = 0
    while True:
        n += 1
        yield n


_id_counter_inst = _id_counter()


def _unique_point(**kwargs) -> dict:
    n = next(_id_counter_inst)
    return {
        "city": f"City{n}",
        "country": f"CO{n}",
        "RU_city": f"Город{n}",
        "RU_country": f"Страна{n}",
        **kwargs,
    }


@pytest.mark.asyncio
async def test_find_all_paths_dedup_preserves_distinct_routes(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="DedupCo")
        point_a = PointFactory(**_unique_point())
        point_b = PointFactory(**_unique_point())
        container = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
        session.add_all([company, point_a, point_b, container])
        await session.flush()

        route1 = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteSegmentType.RAIL,
            effective_from=datetime.date(2024, 1, 1),
            effective_to=datetime.date(2025, 6, 30),
            container_owner=ContainerOwner.COC,
        )
        route2 = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteSegmentType.RAIL,
            effective_from=datetime.date(2024, 1, 1),
            effective_to=datetime.date(2025, 12, 31),
            container_owner=ContainerOwner.SOC,
        )
        session.add_all([route1, route2])
        await session.flush()

        price1 = PriceFactory(route_id=route1.id, container_id=container.id)
        price2 = PriceFactory(route_id=route2.id, container_id=container.id)
        session.add_all([price1, price2])
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container.id],
        )

    assert len(result) == 2
    owners = {s.container_owner for r in result for s in r.segments}
    assert owners == {"COC", "SOC"}


@pytest.mark.asyncio
async def test_find_all_paths_dedup_multiple_prices(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        company = CompanyFactory(name="MultiPriceCo")
        point_a = PointFactory(**_unique_point())
        point_b = PointFactory(**_unique_point())
        container_20 = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
        container_40 = ContainerFactory(size=40, weight_from=0, weight_to=28000, name="40DC", type=ContainerType.DC)
        session.add_all([company, point_a, point_b, container_20, container_40])
        await session.flush()

        route = RouteSegmentFactory(
            company_id=company.id,
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            type=RouteSegmentType.RAIL,
        )
        session.add(route)
        await session.flush()

        price_20 = PriceFactory(route_id=route.id, container_id=container_20.id)
        price_40 = PriceFactory(route_id=route.id, container_id=container_40.id)
        session.add_all([price_20, price_40])
        await session.commit()

    with patch("module_data_internal.aggregators.routes.get_database", return_value=sqlite_db):
        result = await find_all_paths(
            date=datetime.date(2024, 6, 15),
            start_point_id=point_a.id,
            end_point_id=point_b.id,
            container_ids=[container_20.id, container_40.id],
        )

    assert len(result) == 1
    route_result = result[0]
    assert len(route_result.segments) == 1
    assert route_result.segments[0].company == "MultiPriceCo"
