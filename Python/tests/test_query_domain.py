"""Tests for Query Composer domain model and compiler."""

import datetime

from module_data_internal.aggregators.rules import CocSocRule, DropAwareConnection, ThroughRule
from module_data_internal.query_domain.compiler import QueryCompiler
from module_data_internal.query_domain.connection import RouteSegmentConnection
from module_data_internal.query_domain.connection_rules import MatchesEndpoint
from module_data_internal.query_domain.drop import DropConnection
from module_data_internal.query_domain.drop_rules import (
    DropEffectiveOn,
    DropMatchesCompany,
    DropMatchesContainer,
    DropMatchesEndpoint,
)
from module_data_internal.query_domain.filters import (
    AtEndPoint,
    AtStartPoint,
    EffectiveOn,
    ExcludeOwners,
    NoDropOff,
)
from module_data_internal.query_domain.route import Route
from module_data_internal.query_domain.segment import RouteSegment
from module_data_internal.schemas import (
    ContainerOwner,
    DropModel,
    PriceModel,
    RouteModel,
    RouteType,
)
from sqlalchemy.orm import aliased

# ── route helpers for tests ───────────────────────────────────────────


def _base_segment(route_type: RouteType) -> RouteSegment:
    return (
        RouteSegment(route_type)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
        .add_filter(AtEndPoint())
        .add_filter(NoDropOff())
    )


def rail_direct() -> Route:
    return Route(segments=[_base_segment(RouteType.RAIL)], connections=[])


def sea_direct() -> Route:
    return Route(segments=[_base_segment(RouteType.SEA)], connections=[])


def sea_rail_combined(hide_soc: bool = False) -> Route:
    soc_filter = ExcludeOwners([ContainerOwner.SOC]) if hide_soc else None
    sea = RouteSegment(RouteType.SEA)
    sea.add_filter(EffectiveOn())
    sea.add_filter(AtStartPoint())
    sea.add_filter(soc_filter)

    rail = RouteSegment(RouteType.RAIL)
    rail.add_filter(EffectiveOn())
    rail.add_filter(AtEndPoint())

    bridge = DropAwareConnection()
    drop = DropConnection(bridge=bridge, required=False)
    drop.rule(DropMatchesEndpoint())
    drop.rule(DropMatchesCompany())
    drop.rule(DropMatchesContainer())
    drop.rule(DropEffectiveOn())

    conn = RouteSegmentConnection(from_seg=sea, to_seg=rail)
    conn.with_drop_aware_bridge(bridge)
    conn.rule(CocSocRule())
    conn.rule(ThroughRule())
    conn.with_drop(drop)
    return Route(segments=[sea, rail], connections=[conn])


def _route_aliases():
    """Create aliased RouteModel pairs for unit-testing connection rules."""
    return aliased(RouteModel), aliased(RouteModel)


def _drop_aliases():
    """Create aliased from/to RouteModel + DropModel + PriceModel for drop rules."""
    from_seg = aliased(RouteModel)
    to_seg = aliased(RouteModel)
    drop = aliased(DropModel)
    from_price = aliased(PriceModel)
    to_price = aliased(PriceModel)
    return from_seg, to_seg, drop, from_price, to_price

# ── RouteSegment ──────────────────────────────────────────────────────


class TestRouteSegment:
    def test_create_with_type(self):
        seg = RouteSegment(RouteType.RAIL)
        assert seg.route_type == RouteType.RAIL
        assert seg._filters == []
        assert seg._container_ids == []

    def test_add_filter_returns_self(self):
        seg = RouteSegment(RouteType.SEA)
        result = seg.add_filter(EffectiveOn())
        assert result is seg

    def test_add_filter_none_is_ignored(self):
        seg = RouteSegment(RouteType.SEA)
        seg.add_filter(None)
        assert seg._filters == []

    def test_chain_filters(self):
        seg = (
            RouteSegment(RouteType.RAIL)
            .add_filter(EffectiveOn())
            .add_filter(AtStartPoint())
            .add_filter(AtEndPoint())
        )
        assert len(seg._filters) == 3

    def test_with_containers(self):
        seg = RouteSegment(RouteType.SEA)
        result = seg.with_containers([1, 2, 3])
        assert result is seg
        assert seg._container_ids == [1, 2, 3]

# ── RouteSegmentConnection ────────────────────────────────────────────


class TestRouteSegmentConnection:
    def test_create_with_segments(self):
        seg_a = RouteSegment(RouteType.SEA)
        seg_b = RouteSegment(RouteType.RAIL)
        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
        assert conn.from_seg is seg_a
        assert conn.to_seg is seg_b
        assert conn.drops == []
        assert conn._rules == []

    def test_rule_returns_self(self):
        seg_a = RouteSegment(RouteType.SEA)
        seg_b = RouteSegment(RouteType.RAIL)
        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
        result = conn.rule(MatchesEndpoint())
        assert result is conn
        assert len(conn._rules) == 1

    def test_with_drop_appends(self):
        seg_a = RouteSegment(RouteType.SEA)
        seg_b = RouteSegment(RouteType.RAIL)
        drop1 = DropConnection(required=False)
        drop2 = DropConnection(required=True)
        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
        conn.with_drop(drop1).with_drop(drop2)
        assert len(conn.drops) == 2
        assert conn.drops[0] is drop1
        assert conn.drops[1] is drop2

    def test_build_condition_single_rule(self):
        seg_a = RouteSegment(RouteType.SEA)
        seg_b = RouteSegment(RouteType.RAIL)
        from_alias, to_alias = _route_aliases()
        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
        conn.rule(MatchesEndpoint())
        condition = conn.build_condition(from_alias, to_alias)
        assert condition is not None

    def test_build_condition_multiple_rules(self):
        seg_a = RouteSegment(RouteType.SEA)
        seg_b = RouteSegment(RouteType.RAIL)
        from_alias, to_alias = _route_aliases()
        conn = (
            RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
            .rule(MatchesEndpoint())
            .rule(CocSocRule())
        )
        condition = conn.build_condition(from_alias, to_alias)
        assert condition is not None

# ── DropConnection ────────────────────────────────────────────────────


class TestDropConnection:
    def test_create(self):
        drop = DropConnection(required=False)
        assert drop.required is False
        assert drop.bridge is None
        assert drop._rules == []

    def test_create_with_bridge(self):
        bridge = DropAwareConnection()
        drop = DropConnection(bridge=bridge, required=True)
        assert drop.bridge is bridge
        assert drop.required is True

    def test_rule_chain(self):
        drop = (
            DropConnection(required=True)
            .rule(DropMatchesEndpoint())
            .rule(DropMatchesCompany())
        )
        assert drop.required is True
        assert len(drop._rules) == 2

    def test_build_condition(self):
        drop = DropConnection()
        drop.rule(DropMatchesEndpoint())
        drop.rule(DropMatchesCompany())
        drop.rule(DropMatchesContainer())
        drop.rule(DropEffectiveOn())
        from_alias, to_alias, drop_alias, from_price, to_price = _drop_aliases()
        condition = drop.build_condition(
            from_alias, to_alias, drop_alias, from_price, to_price,
            datetime.date(2024, 6, 15),
        )
        assert condition is not None

# ── Route ─────────────────────────────────────────────────────────────


class TestRoute:
    def test_single_segment(self):
        seg = RouteSegment(RouteType.RAIL)
        route = Route(segments=[seg])
        assert len(route.segments) == 1
        assert route.connections == []

    def test_two_segments_with_connection(self):
        sea = RouteSegment(RouteType.SEA)
        rail = RouteSegment(RouteType.RAIL)
        conn = RouteSegmentConnection(from_seg=sea, to_seg=rail)
        route = Route(segments=[sea, rail], connections=[conn])
        assert len(route.segments) == 2
        assert len(route.connections) == 1

    def test_three_segments(self):
        seg_a = RouteSegment(RouteType.SEA)
        seg_b = RouteSegment(RouteType.RAIL)
        seg_c = RouteSegment(RouteType.SEA)
        conn_ab = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
        conn_bc = RouteSegmentConnection(from_seg=seg_b, to_seg=seg_c)
        route = Route(segments=[seg_a, seg_b, seg_c], connections=[conn_ab, conn_bc])
        assert len(route.segments) == 3
        assert len(route.connections) == 2

# ── Filters ───────────────────────────────────────────────────────────


class TestFilters:
    def test_effective_on(self):
        alias = aliased(RouteModel)
        f = EffectiveOn()
        expr = f.to_sql(alias, datetime.date(2024, 6, 15), 1, 2)
        assert expr is not None

    def test_at_start_point_with_dep_id(self):
        alias = aliased(RouteModel)
        f = AtStartPoint()
        expr = f.to_sql(alias, datetime.date(2024, 6, 15), 10, 20)
        assert expr is not None

    def test_at_start_point_with_explicit_id(self):
        alias = aliased(RouteModel)
        f = AtStartPoint(start_id=42)
        expr = f.to_sql(alias, datetime.date(2024, 6, 15), 10, 20)
        assert expr is not None

    def test_at_end_point(self):
        alias = aliased(RouteModel)
        f = AtEndPoint()
        expr = f.to_sql(alias, datetime.date(2024, 6, 15), 10, 20)
        assert expr is not None

    def test_exclude_owners_with_owners(self):
        alias = aliased(RouteModel)
        f = ExcludeOwners([ContainerOwner.SOC])
        expr = f.to_sql(alias, datetime.date(2024, 6, 15), 1, 2)
        assert expr is not None

    def test_exclude_owners_empty(self):
        alias = aliased(RouteModel)
        f = ExcludeOwners([])
        expr = f.to_sql(alias, datetime.date(2024, 6, 15), 1, 2)
        assert expr is not None

    def test_no_drop_off(self):
        alias = aliased(RouteModel)
        f = NoDropOff()
        expr = f.to_sql(alias, datetime.date(2024, 6, 15), 1, 2)
        assert expr is not None

# ── Connection Rules ──────────────────────────────────────────────────


class TestConnectionRules:
    def test_matches_endpoint(self):
        from_alias, to_alias = _route_aliases()
        rule = MatchesEndpoint()
        expr = rule.to_sql(from_alias, to_alias)
        assert expr is not None

    def test_drop_aware_endpoint(self):
        from_alias, to_alias = _route_aliases()
        bridge = DropAwareConnection()
        expr = bridge.build_segment_condition(from_alias, to_alias)
        assert expr is not None

    def test_drop_aware_connection_modify_drop_join(self):
        from_alias, to_alias, drop_alias, from_price, to_price = _drop_aliases()
        bridge = DropAwareConnection()
        date = datetime.date(2024, 6, 15)
        rules_cond = DropMatchesEndpoint().to_sql(
            from_alias, to_alias, drop_alias, from_price, to_price, date,
        )
        join_cond, where_cond = bridge.modify_drop_join(from_alias, drop_alias, rules_cond)
        assert join_cond is not None
        assert where_cond is not None

    def test_coc_soc_logic(self):
        from_alias, to_alias = _route_aliases()
        rule = CocSocRule()
        expr = rule.to_sql(from_alias, to_alias)
        assert expr is not None

    def test_through_logic(self):
        from_alias, to_alias = _route_aliases()
        rule = ThroughRule()
        expr = rule.to_sql(from_alias, to_alias)
        assert expr is not None

# ── Drop Rules ────────────────────────────────────────────────────────


class TestDropRules:
    def test_drop_matches_endpoint(self):
        from_alias, to_alias, drop_alias, from_price, to_price = _drop_aliases()
        rule = DropMatchesEndpoint()
        expr = rule.to_sql(from_alias, to_alias, drop_alias, from_price, to_price, datetime.date(2024, 6, 15))
        assert expr is not None

    def test_drop_matches_company(self):
        from_alias, to_alias, drop_alias, from_price, to_price = _drop_aliases()
        rule = DropMatchesCompany()
        expr = rule.to_sql(from_alias, to_alias, drop_alias, from_price, to_price, datetime.date(2024, 6, 15))
        assert expr is not None

    def test_drop_matches_container(self):
        from_alias, to_alias, drop_alias, from_price, to_price = _drop_aliases()
        rule = DropMatchesContainer()
        expr = rule.to_sql(from_alias, to_alias, drop_alias, from_price, to_price, datetime.date(2024, 6, 15))
        assert expr is not None

    def test_drop_effective_on(self):
        from_alias, to_alias, drop_alias, from_price, to_price = _drop_aliases()
        rule = DropEffectiveOn()
        expr = rule.to_sql(from_alias, to_alias, drop_alias, from_price, to_price, datetime.date(2024, 6, 15))
        assert expr is not None

# ── Templates ─────────────────────────────────────────────────────────


class TestTemplates:
    def test_rail_direct(self):
        route = rail_direct()
        assert len(route.segments) == 1
        assert route.segments[0].route_type == RouteType.RAIL
        assert len(route.connections) == 0

    def test_sea_direct(self):
        route = sea_direct()
        assert len(route.segments) == 1
        assert route.segments[0].route_type == RouteType.SEA
        assert len(route.connections) == 0

    def test_sea_rail_combined(self):
        route = sea_rail_combined()
        assert len(route.segments) == 2
        assert route.segments[0].route_type == RouteType.SEA
        assert route.segments[1].route_type == RouteType.RAIL
        assert len(route.connections) == 1
        conn = route.connections[0]
        assert conn.from_seg is route.segments[0]
        assert conn.to_seg is route.segments[1]
        assert len(conn.drops) == 1
        assert isinstance(conn.drops[0].bridge, DropAwareConnection)
        assert len(conn.drops[0]._rules) == 4

    def test_sea_rail_combined_with_hide_soc(self):
        route = sea_rail_combined(hide_soc=True)
        sea_seg = route.segments[0]
        has_exclude = any(isinstance(f, ExcludeOwners) for f in sea_seg._filters)
        assert has_exclude

    def test_sea_rail_combined_without_hide_soc(self):
        route = sea_rail_combined(hide_soc=False)
        sea_seg = route.segments[0]
        has_exclude = any(isinstance(f, ExcludeOwners) for f in sea_seg._filters)
        assert not has_exclude


class TestQueryCompiler:
    """Test that QueryCompiler builds valid SQLAlchemy Select for various configs."""

    def setup_method(self):
        self.date = datetime.date(2024, 6, 15)
        self.dep_id = 1
        self.dest_id = 2
        self.container_ids = [10, 20]

    def _sql(self, stmt) -> str:
        return str(stmt.compile(compile_kwargs={"literal_binds": True}))

    def test_direct_rail(self):
        compiler = QueryCompiler(rail_direct())
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "seg_0" in sql
        assert "price_0" in sql

    def test_direct_sea(self):
        compiler = QueryCompiler(sea_direct())
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "seg_0" in sql

    def test_combined_sea_rail(self):
        compiler = QueryCompiler(sea_rail_combined())
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "seg_0" in sql
        assert "seg_1" in sql
        assert "price_0" in sql
        assert "price_1" in sql
        assert "drop_0" in sql

    def test_three_segments_no_drop(self):
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
        seg_c = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtEndPoint())

        conn_ab = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b).rule(MatchesEndpoint())
        conn_bc = RouteSegmentConnection(from_seg=seg_b, to_seg=seg_c).rule(MatchesEndpoint())

        route = Route(segments=[seg_a, seg_b, seg_c], connections=[conn_ab, conn_bc])
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "seg_0" in sql
        assert "seg_1" in sql
        assert "seg_2" in sql
        assert "price_0" in sql
        assert "price_1" in sql
        assert "price_2" in sql
        assert "LEFT OUTER JOIN DROP" not in sql.upper()

    def test_three_segments_with_drop(self):
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
        seg_c = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtEndPoint())

        drop = DropConnection(bridge=DropAwareConnection())
        drop.rule(DropMatchesEndpoint())
        drop.rule(DropMatchesCompany())
        drop.rule(DropMatchesContainer())
        drop.rule(DropEffectiveOn())

        conn_ab = (
            RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
            .rule(MatchesEndpoint())
            .with_drop(drop)
        )
        conn_bc = RouteSegmentConnection(from_seg=seg_b, to_seg=seg_c).rule(MatchesEndpoint())

        route = Route(segments=[seg_a, seg_b, seg_c], connections=[conn_ab, conn_bc])
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "seg_0" in sql
        assert "seg_1" in sql
        assert "seg_2" in sql
        assert "DROP AS DROP_0" in sql.upper()

    def test_container_ids_per_segment(self):
        seg_a = RouteSegment(RouteType.SEA).with_containers([100])
        seg_a.add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).with_containers([200])
        seg_b.add_filter(EffectiveOn()).add_filter(AtEndPoint())

        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b).rule(MatchesEndpoint())
        route = Route(segments=[seg_a, seg_b], connections=[conn])

        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "100" in sql
        assert "200" in sql

    def test_fallback_to_global_container_ids(self):
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn()).add_filter(AtEndPoint())

        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b).rule(MatchesEndpoint())
        route = Route(segments=[seg_a, seg_b], connections=[conn])

        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "10" in sql
        assert "20" in sql

    def test_drop_off_excluded_when_no_drops(self):
        compiler = QueryCompiler(rail_direct())
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "LEFT OUTER JOIN DROP" not in sql.upper()
        assert "INNER JOIN DROP" not in sql.upper()

    def test_ordering_by_effective_to(self):
        compiler = QueryCompiler(rail_direct())
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "DESC" in sql.upper()

    def test_single_segment_multiple_filters(self):
        seg = RouteSegment(RouteType.SEA)
        seg.add_filter(EffectiveOn())
        seg.add_filter(AtStartPoint(start_id=42))
        seg.add_filter(AtEndPoint(end_id=99))
        seg.add_filter(NoDropOff())
        route = Route(segments=[seg])
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "42" in sql
        assert "99" in sql

    def test_hidden_soc_filtered(self):
        compiler = QueryCompiler(sea_rail_combined(hide_soc=True))
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "SOC" in sql or "soc" in sql.lower()


class TestMultiDrop:
    """Test multiple drop-offs on a single connection."""

    def setup_method(self):
        self.date = datetime.date(2024, 6, 15)
        self.dep_id = 1
        self.dest_id = 2
        self.container_ids = [10, 20]

    def _sql(self, stmt) -> str:
        return str(stmt.compile(compile_kwargs={"literal_binds": True}))

    def _make_two_drop_route(self, drop1: DropConnection, drop2: DropConnection) -> Route:
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn()).add_filter(AtEndPoint())
        conn = (
            RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
            .rule(MatchesEndpoint())
            .with_drop(drop1)
            .with_drop(drop2)
        )
        return Route(segments=[seg_a, seg_b], connections=[conn])

    def test_two_drops_both_optional_on_column(self):
        drop1 = DropConnection(bridge=DropAwareConnection(), required=False).rule(DropMatchesEndpoint())
        drop2 = DropConnection(bridge=DropAwareConnection(), required=False).rule(DropMatchesCompany())
        route = self._make_two_drop_route(drop1, drop2)
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "DROP AS DROP_0" in sql.upper()
        assert "DROP AS DROP_1" in sql.upper()
        # Both are LEFT JOINs (optional)
        assert sql.upper().count("LEFT OUTER JOIN DROP") == 2

    def test_two_drops_both_required_on_column(self):
        drop1 = DropConnection(bridge=DropAwareConnection(), required=True).rule(DropMatchesEndpoint())
        drop2 = DropConnection(bridge=DropAwareConnection(), required=True).rule(DropMatchesCompany())
        route = self._make_two_drop_route(drop1, drop2)
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        # Both are JOINs (required + on column) — no LEFT OUTER
        assert "LEFT OUTER JOIN DROP" not in sql.upper()
        assert "DROP AS DROP_0" in sql.upper()
        assert "DROP AS DROP_1" in sql.upper()

    def test_two_drops_mixed_required_optional_on_column(self):
        drop1 = DropConnection(bridge=DropAwareConnection(), required=True).rule(DropMatchesEndpoint())
        drop2 = DropConnection(bridge=DropAwareConnection(), required=False).rule(DropMatchesCompany())
        route = self._make_two_drop_route(drop1, drop2)
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        # drop_0: JOIN (required), drop_1: LEFT OUTER (optional)
        assert "LEFT OUTER JOIN DROP AS DROP_1" in sql.upper()
        assert "JOIN DROP AS DROP_0" in sql.upper()
        # Verify drop_0 is NOT a LEFT OUTER
        assert "LEFT OUTER JOIN DROP AS DROP_0" not in sql.upper()

    def test_two_drops_on_none_optional(self):
        drop1 = DropConnection(required=False).rule(DropMatchesEndpoint())
        drop2 = DropConnection(required=False).rule(DropMatchesCompany())
        route = self._make_two_drop_route(drop1, drop2)
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        # Both LEFT JOINs (optional, no on column)
        assert sql.upper().count("LEFT OUTER JOIN DROP") == 2
        # No WHERE for on column (check only WHERE clause)
        where_clause = sql.lower().split("\nwhere")[1] if "\nwhere" in sql.lower() else ""
        assert "dropp_off_point_id is not null or" not in where_clause

    def test_two_drops_on_none_required(self):
        drop1 = DropConnection(required=True).rule(DropMatchesEndpoint())
        drop2 = DropConnection(required=True).rule(DropMatchesCompany())
        route = self._make_two_drop_route(drop1, drop2)
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        # Both JOINs (required, no on column) — no LEFT OUTER
        assert "LEFT OUTER JOIN DROP" not in sql.upper()
        assert "DROP AS DROP_0" in sql.upper()
        assert "DROP AS DROP_1" in sql.upper()

    def test_and_semantics_for_required_drops(self):
        """Both required drops must match — SQL has AND via two WHERE clauses."""
        drop1 = DropConnection(bridge=DropAwareConnection(), required=True).rule(DropMatchesEndpoint())
        drop2 = DropConnection(bridge=DropAwareConnection(), required=True).rule(DropMatchesCompany())
        route = self._make_two_drop_route(drop1, drop2)
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        # Two separate WHERE clauses → AND semantics
        # Each has: dropp_off_point_id IS NOT NULL OR drop_N.id IS NOT NULL
        where_parts = sql.lower().split("where")
        on_col_where = [w for w in where_parts if "dropp_off_point_id" in w and "drop_" in w]
        assert len(on_col_where) == 2

    def test_three_drops(self):
        drop1 = DropConnection(bridge=DropAwareConnection(), required=False).rule(DropMatchesEndpoint())
        drop2 = DropConnection(required=False).rule(DropMatchesCompany())
        drop3 = DropConnection(required=True).rule(DropMatchesContainer())
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn()).add_filter(AtEndPoint())
        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b)
        conn.rule(MatchesEndpoint())
        conn.with_drop(drop1)
        conn.with_drop(drop2)
        conn.with_drop(drop3)
        route = Route(segments=[seg_a, seg_b], connections=[conn])
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "DROP AS DROP_0" in sql.upper()
        assert "DROP AS DROP_1" in sql.upper()
        assert "DROP AS DROP_2" in sql.upper()
        # drop_0: LEFT (optional+on), drop_1: LEFT (optional+none), drop_2: JOIN (required+none)
        assert "LEFT OUTER JOIN DROP AS DROP_0" in sql.upper()
        assert "LEFT OUTER JOIN DROP AS DROP_1" in sql.upper()
        assert "JOIN DROP AS DROP_2" in sql.upper()
        assert "LEFT OUTER JOIN DROP AS DROP_2" not in sql.upper()

    def test_drop_on_none_independent_from_column(self):
        """Drop with on=None does not reference dropp_off_point_id in JOIN/WHERE."""
        drop = DropConnection(required=False).rule(DropMatchesEndpoint())
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn()).add_filter(AtEndPoint())
        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b).rule(MatchesEndpoint()).with_drop(drop)
        route = Route(segments=[seg_a, seg_b], connections=[conn])
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        # dropp_off_point_id only appears from filters, not from drop logic
        where_part = sql.lower().split("where")[1] if "where" in sql.lower() else ""
        # No "dropp_off_point_id IS NOT NULL OR drop" pattern (that's the on= coupling)
        assert "dropp_off_point_id is not null or" not in where_part

    def test_drop_on_column_references_column(self):
        """Drop with on='dropp_off_point_id' adds IS NULL join + IS NOT NULL WHERE."""
        drop = DropConnection(bridge=DropAwareConnection(), required=False).rule(DropMatchesEndpoint())
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn()).add_filter(AtEndPoint())
        conn = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b).rule(MatchesEndpoint()).with_drop(drop)
        route = Route(segments=[seg_a, seg_b], connections=[conn])
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        where_part = sql.lower().split("where")[1] if "where" in sql.lower() else ""
        assert "dropp_off_point_id is not null or" in where_part

    def test_compiler_reuse(self):
        """Compiler can be reused — build() produces independent SELECT statements."""
        compiler = QueryCompiler(rail_direct())
        stmt1 = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        stmt2 = compiler.build(self.date, self.dep_id, self.dest_id, [30, 40])
        sql1 = self._sql(stmt1)
        sql2 = self._sql(stmt2)
        assert "10" in sql1
        assert "30" in sql2
        assert "10" not in sql2

    def test_two_drops_on_different_connections(self):
        """Each connection can have its own drops."""
        seg_a = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        seg_b = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
        seg_c = RouteSegment(RouteType.SEA).add_filter(EffectiveOn()).add_filter(AtEndPoint())

        drop1 = DropConnection(bridge=DropAwareConnection(), required=False).rule(DropMatchesEndpoint())
        drop2 = DropConnection(required=True).rule(DropMatchesCompany())

        conn_ab = RouteSegmentConnection(from_seg=seg_a, to_seg=seg_b).rule(MatchesEndpoint()).with_drop(drop1)
        conn_bc = RouteSegmentConnection(from_seg=seg_b, to_seg=seg_c).rule(MatchesEndpoint()).with_drop(drop2)

        route = Route(segments=[seg_a, seg_b, seg_c], connections=[conn_ab, conn_bc])
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "LEFT OUTER JOIN DROP AS DROP_0" in sql.upper()
        assert "JOIN DROP AS DROP_1" in sql.upper()
        assert "LEFT OUTER JOIN DROP AS DROP_1" not in sql.upper()


# ── AUTO routes ─────────────────────────────────────────────────────


def _auto_direct():
    return Route(segments=[_base_segment(RouteType.AUTO)], connections=[])


def _auto_rail_combined():
    auto = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    rail = (
        RouteSegment(RouteType.RAIL)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    return Route(
        segments=[auto, rail],
        connections=[RouteSegmentConnection(from_seg=auto, to_seg=rail).rule(MatchesEndpoint())],
    )


def _rail_auto_combined():
    rail = (
        RouteSegment(RouteType.RAIL)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    auto = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    return Route(
        segments=[rail, auto],
        connections=[RouteSegmentConnection(from_seg=rail, to_seg=auto).rule(MatchesEndpoint())],
    )


def _auto_rail_auto_combined():
    auto1 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    rail = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
    auto2 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    return Route(
        segments=[auto1, rail, auto2],
        connections=[
            RouteSegmentConnection(from_seg=auto1, to_seg=rail).rule(MatchesEndpoint()),
            RouteSegmentConnection(from_seg=rail, to_seg=auto2).rule(MatchesEndpoint()),
        ],
    )


def _auto_sea_rail_auto_combined():
    auto1 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    sea = RouteSegment(RouteType.SEA).add_filter(EffectiveOn())
    rail = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
    auto2 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    bridge = DropAwareConnection()
    drop = DropConnection(bridge=bridge, required=False)
    return Route(
        segments=[auto1, sea, rail, auto2],
        connections=[
            RouteSegmentConnection(from_seg=auto1, to_seg=sea).rule(MatchesEndpoint()),
            RouteSegmentConnection(from_seg=sea, to_seg=rail)
            .with_drop_aware_bridge(bridge)
            .rule(CocSocRule())
            .rule(ThroughRule())
            .with_drop(drop),
            RouteSegmentConnection(from_seg=rail, to_seg=auto2).rule(MatchesEndpoint()),
        ],
    )


class TestAutoRoutes:
    date = datetime.date(2026, 6, 1)
    dep_id = 1
    dest_id = 2
    container_ids = [10, 20]

    def _sql(self, stmt):
        return str(stmt.compile(compile_kwargs={"literal_binds": True}))

    def test_direct_auto(self):
        route = _auto_direct()
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "routes AS seg_0" in sql
        assert "RAIL" not in sql.upper()
        assert "SEA" not in sql.upper()

    def test_combined_auto_rail(self):
        route = _auto_rail_combined()
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "routes AS seg_0" in sql
        assert "routes AS seg_1" in sql

    def test_combined_rail_auto(self):
        route = _rail_auto_combined()
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "routes AS seg_0" in sql
        assert "routes AS seg_1" in sql

    def test_combined_auto_rail_auto(self):
        route = _auto_rail_auto_combined()
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "routes AS seg_0" in sql
        assert "routes AS seg_1" in sql
        assert "routes AS seg_2" in sql

    def test_combined_auto_sea_rail_auto(self):
        route = _auto_sea_rail_auto_combined()
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "routes AS seg_0" in sql
        assert "routes AS seg_1" in sql
        assert "routes AS seg_2" in sql
        assert "routes AS seg_3" in sql

    def test_auto_sea_rail_auto_with_hide_soc_sql(self):
        auto1 = RouteSegment(RouteType.AUTO).add_filter(EffectiveOn()).add_filter(AtStartPoint())
        sea = (
            RouteSegment(RouteType.SEA)
            .add_filter(EffectiveOn())
            .add_filter(ExcludeOwners([ContainerOwner.SOC]))
        )
        rail = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
        auto2 = RouteSegment(RouteType.AUTO).add_filter(EffectiveOn()).add_filter(AtEndPoint())
        bridge = DropAwareConnection()
        drop = DropConnection(bridge=bridge, required=False)
        route = Route(
            segments=[auto1, sea, rail, auto2],
            connections=[
                RouteSegmentConnection(from_seg=auto1, to_seg=sea).rule(MatchesEndpoint()),
                RouteSegmentConnection(from_seg=sea, to_seg=rail)
                .with_drop_aware_bridge(bridge)
                .rule(CocSocRule())
                .rule(ThroughRule())
                .with_drop(drop),
                RouteSegmentConnection(from_seg=rail, to_seg=auto2).rule(MatchesEndpoint()),
            ],
        )
        compiler = QueryCompiler(route)
        stmt = compiler.build(self.date, self.dep_id, self.dest_id, self.container_ids)
        sql = self._sql(stmt)
        assert "container_owner" in sql.lower()
        assert "routes AS seg_0" in sql
        assert "routes AS seg_1" in sql
        assert "routes AS seg_2" in sql
        assert "routes AS seg_3" in sql
