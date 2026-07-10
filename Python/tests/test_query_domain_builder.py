import datetime

import pytest
from module_data_internal.query_domain import DropOff, RouteBuilder, Segment


class TestRouteBuilderAPI:
    def test_no_segments_raises(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        with pytest.raises(RuntimeError, match="No segments defined"):
            rb.build()

    def test_setters_return_self(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        assert rb.set_containers([1, 2]) is rb
        assert rb.set_container(1) is rb
        assert rb.set_start_point(1) is rb
        assert rb.set_start_points([1, 2]) is rb
        assert rb.set_end_point(1) is rb
        assert rb.set_end_points([1, 2]) is rb
        assert rb.set_companies([1]) is rb
        assert rb.set_company(1) is rb

    def test_copy_returns_new_builder_with_same_segments(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        seg1 = Segment()
        seg2 = Segment()
        rb.add_segment(seg1)
        rb.add_segment(seg2, conditions=seg1.end_point.equals(seg2.start_point))

        cp = rb.copy()
        assert cp is not rb
        assert len(cp._segments) == 2
        assert len(cp._connections) == 1
        assert cp._date == rb._date
        assert cp._container_ids == rb._container_ids
        assert cp._start_point_id == rb._start_point_id
        assert cp._end_point_id == rb._end_point_id

    def test_copy_then_add_segment(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        seg1 = Segment()
        seg2 = Segment()
        rb.add_segment(seg1)
        rb.add_segment(seg2, conditions=seg1.end_point.equals(seg2.start_point))

        cp = rb.copy().add_segment(Segment())
        assert len(cp._segments) == 3
        assert len(cp._connections) == 2
        assert len(rb._segments) == 2

    def test_add_segment_with_single_condition(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        s1 = Segment()
        s2 = Segment()
        rb.add_segment(s1)
        rb.add_segment(s2, conditions=s1.end_point.equals(s2.start_point))
        assert len(rb._segments) == 2
        assert len(rb._connections) == 1
        assert rb._connections[0][0].op == "eq"

    def test_add_segment_with_multiple_conditions(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        s1 = Segment()
        s2 = Segment()
        rb.add_segment(s1)
        rb.add_segment(
            s2,
            conditions=(
                s1.end_point.equals(s2.start_point),
                s1.company.equals(s2.company),
            ),
        )
        assert len(rb._connections[0]) == 2

    def test_add_segment_no_conditions_defaults_empty(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        s1 = Segment()
        s2 = Segment()
        rb.add_segment(s1)
        rb.add_segment(s2)
        from collections import deque

        assert rb._connections == deque([[]])

    def test_add_condition(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        seg = Segment()
        rb.add_segment(seg)
        rb.add_condition(seg.drop_off_point.null())
        assert len(rb._global_conditions) == 1

    def test_add_drop_off_no_conditions(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        seg = Segment()
        drop = DropOff()
        rb.add_segment(seg)
        rb.add_drop_off(drop)
        assert len(rb._drops) == 1
        assert rb._drops[0][1] == []

    def test_add_drop_off_with_conditions(self) -> None:
        rb = RouteBuilder(datetime.date.today())
        seg = Segment()
        drop = DropOff()
        rb.add_segment(seg)
        rb.add_drop_off(drop, conditions=drop.company.equals(seg.company))
        assert len(rb._drops[0][1]) == 1

    def test_chaining(self) -> None:
        s1 = Segment()
        s2 = Segment()
        rb = (
            RouteBuilder(datetime.date.today())
            .set_containers([1, 2])
            .set_start_point(10)
            .set_end_point(20)
            .add_segment(s1)
            .add_segment(s2, conditions=s1.end_point.equals(s2.start_point))
            .add_condition(s1.drop_off_point.null())
        )
        assert len(rb._segments) == 2
        assert len(rb._global_conditions) == 1

    def test_prepend_segment_single(self) -> None:
        from module_data_internal.schemas import RouteType

        s1 = Segment(_type=RouteType.RAIL)
        s0 = Segment(_type=RouteType.SEA)
        rb = (
            RouteBuilder(datetime.date.today())
            .add_segment(s1)
            .prepend_segment(s0, conditions=s0.end_point.equals(s1.start_point))
        )
        assert len(rb._segments) == 2
        assert rb._segments[0]._type_filter is RouteType.SEA
        assert rb._segments[1]._type_filter is RouteType.RAIL
        assert len(rb._connections) == 1
        assert rb._connections[0][0].op == "eq"

    def test_prepend_segment_no_conditions(self) -> None:
        from module_data_internal.schemas import RouteType

        s1 = Segment(_type=RouteType.RAIL)
        s0 = Segment(_type=RouteType.SEA)
        rb = (
            RouteBuilder(datetime.date.today())
            .add_segment(s1)
            .prepend_segment(s0)
        )
        assert len(rb._segments) == 2
        from collections import deque

        assert rb._connections == deque([[]])

    def test_prepend_segment_multiple(self) -> None:
        from module_data_internal.schemas import RouteType

        s1 = Segment(_type=RouteType.SEA)
        s0 = Segment(_type=RouteType.RAIL)
        s_neg1 = Segment(_type=RouteType.SEA)
        rb = (
            RouteBuilder(datetime.date.today())
            .add_segment(s1)
            .prepend_segment(s0, conditions=s0.end_point.equals(s1.start_point))
            .prepend_segment(s_neg1, conditions=s_neg1.end_point.equals(s0.start_point))
        )
        assert len(rb._segments) == 3
        assert rb._segments[0]._type_filter is RouteType.SEA
        assert rb._segments[1]._type_filter is RouteType.RAIL
        assert rb._segments[2]._type_filter is RouteType.SEA
        assert len(rb._connections) == 2
        assert rb._connections[0][0].op == "eq"
        assert rb._connections[1][0].op == "eq"

    def test_prepend_segment_returns_self(self) -> None:
        s1 = Segment()
        s0 = Segment()
        rb = RouteBuilder(datetime.date.today()).add_segment(s1)
        assert rb.prepend_segment(s0) is rb

    def test_prepend_then_add(self) -> None:
        from module_data_internal.schemas import RouteType

        s1 = Segment(_type=RouteType.RAIL)
        s2 = Segment(_type=RouteType.SEA)
        s0 = Segment(_type=RouteType.RAIL)
        rb = (
            RouteBuilder(datetime.date.today())
            .add_segment(s1)
            .add_segment(s2, conditions=s1.end_point.equals(s2.start_point))
            .prepend_segment(s0, conditions=s0.end_point.equals(s1.start_point))
        )
        assert len(rb._segments) == 3
        assert rb._segments[0]._type_filter is RouteType.RAIL
        assert rb._segments[1]._type_filter is RouteType.RAIL
        assert rb._segments[2]._type_filter is RouteType.SEA
        assert len(rb._connections) == 2


class TestRouteBuilderBuild:
    async def _run(self, rb: RouteBuilder, session):
        stmt = rb.build()
        result = await session.execute(stmt)
        return result.unique().all()

    async def test_build_single_segment(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Vladivostok"),
                ContainerFactory(id=1),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2),
                PriceFactory(route_id=1, container_id=1),
            ])
        await sqlite_session.commit()

        seg = Segment(_type="RAIL")
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(2)
            .add_segment(seg)
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) == 1

    async def test_build_two_segments_connected(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1),
                ContainerFactory(id=1),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Spb"),
                PointFactory(id=3, city="Vladivostok"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2),
                RouteFactory(id=2, type="RAIL", company_id=1, start_point_id=2, end_point_id=3),
                PriceFactory(route_id=1, container_id=1),
                PriceFactory(route_id=2, container_id=1),
            ])
        await sqlite_session.commit()

        s1 = Segment()
        s2 = Segment()
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(3)
            .add_segment(s1)
            .add_segment(s2, conditions=s1.end_point.equals(s2.start_point))
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) >= 1

    async def test_build_with_drop_off(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            DropFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1),
                ContainerFactory(id=1),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Vladivostok"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2, dropp_off_point_id=2),
                PriceFactory(route_id=1, container_id=1),
                DropFactory(id=1, container_id=1, company_id=1, start_point_id=1, end_point_id=2),
            ])
        await sqlite_session.commit()

        seg = Segment()
        drop_off = DropOff()
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(2)
            .add_segment(seg)
            .add_drop_off(drop_off, conditions=(
                drop_off.container.equals(seg.company),
                drop_off.start_point.equals(2),
            ))
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) >= 1

    async def test_build_type_filter(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1),
                ContainerFactory(id=1),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Vladivostok"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2),
                PriceFactory(route_id=1, container_id=1),
                RouteFactory(id=2, type="SEA", company_id=1, start_point_id=1, end_point_id=2),
                PriceFactory(route_id=2, container_id=1),
            ])
        await sqlite_session.commit()

        seg = Segment(_type="RAIL")
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(2)
            .add_segment(seg)
        )
        rows = await self._run(rb, sqlite_session)
        route_cols = [row._mapping["seg_0"] for row in rows]
        route_types = [r.type for r in route_cols]
        assert all(t.value == "RAIL" for t in route_types)

    async def test_build_multiple_containers(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1),
                ContainerFactory(id=1, name="20DC"),
                ContainerFactory(id=2, name="40HC"),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Vladivostok"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2),
                PriceFactory(route_id=1, container_id=1, value=1000),
                PriceFactory(route_id=1, container_id=2, value=2000),
            ])
        await sqlite_session.commit()

        seg = Segment()
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1, 2])
            .set_start_point(1)
            .set_end_point(2)
            .add_segment(seg)
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) == 1
        route = rows[0]._mapping["seg_0"]
        assert len(route.prices) == 2

    async def test_build_company_filter(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1, name="Company A"),
                CompanyFactory(id=2, name="Company B"),
                ContainerFactory(id=1),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Vladivostok"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2),
                RouteFactory(id=2, type="RAIL", company_id=2, start_point_id=1, end_point_id=2),
                PriceFactory(route_id=1, container_id=1),
                PriceFactory(route_id=2, container_id=1),
            ])
        await sqlite_session.commit()

        seg = Segment()
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(2)
            .set_companies([1])
            .add_segment(seg)
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) == 1
        route = rows[0]._mapping["seg_0"]
        assert route.company_id == 1

    async def test_build_date_filtering(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1),
                ContainerFactory(id=1),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Vladivostok"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2,
                             effective_from=datetime.date(2024, 1, 1),
                             effective_to=datetime.date(2024, 12, 31)),
                RouteFactory(id=2, type="RAIL", company_id=1, start_point_id=1, end_point_id=2,
                             effective_from=datetime.date(2023, 1, 1),
                             effective_to=datetime.date(2023, 12, 31)),
                PriceFactory(route_id=1, container_id=1),
                PriceFactory(route_id=2, container_id=1),
            ])
        await sqlite_session.commit()

        seg = Segment()
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(2)
            .add_segment(seg)
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) == 1
        route = rows[0]._mapping["seg_0"]
        assert route.id == 1

    async def test_build_eager_loads_relationships(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1, name="TestCorp"),
                ContainerFactory(id=1),
                PointFactory(id=1, city="Moscow"),
                PointFactory(id=2, city="Vladivostok"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2),
                PriceFactory(route_id=1, container_id=1),
            ])
        await sqlite_session.commit()

        seg = Segment()
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(2)
            .add_segment(seg)
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) == 1
        route_entity = rows[0]._mapping["seg_0"]
        assert route_entity.company is not None
        assert route_entity.company.name == "TestCorp"
        assert route_entity.start_point is not None
        assert route_entity.start_point.city == "Moscow"
        assert route_entity.end_point is not None
        assert route_entity.end_point.city == "Vladivostok"
        assert len(route_entity.prices) >= 1
        assert route_entity.prices[0].container is not None

    async def test_build_prepend_segment(self, sqlite_session) -> None:
        from tests.data import (
            CompanyFactory,
            ContainerFactory,
            PointFactory,
            PriceFactory,
            RouteFactory,
        )

        async with sqlite_session.begin():
            sqlite_session.add_all([
                CompanyFactory(id=1),
                ContainerFactory(id=1),
                PointFactory(id=1, city="Port"),
                PointFactory(id=2, city="Rail hub"),
                PointFactory(id=3, city="Inland"),
                RouteFactory(id=1, type="RAIL", company_id=1, start_point_id=1, end_point_id=2),
                RouteFactory(id=2, type="SEA", company_id=1, start_point_id=2, end_point_id=3),
                PriceFactory(route_id=1, container_id=1, value=500),
                PriceFactory(route_id=2, container_id=1, value=1500),
            ])
        await sqlite_session.commit()

        rail = Segment(_type="RAIL")
        sea = Segment(_type="SEA")
        rb = (
            RouteBuilder(datetime.date(2024, 6, 15))
            .set_containers([1])
            .set_start_point(1)
            .set_end_point(3)
            .add_segment(sea)
            .prepend_segment(rail, conditions=rail.end_point.equals(sea.start_point))
        )
        rows = await self._run(rb, sqlite_session)
        assert len(rows) == 1
        seg0 = rows[0]._mapping["seg_0"]
        seg1 = rows[0]._mapping["seg_1"]
        assert seg0.type.value == "RAIL"
        assert seg1.type.value == "SEA"
