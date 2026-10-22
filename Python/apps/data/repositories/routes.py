import datetime
from collections.abc import Iterable

from data.internal.query_domain import DropOff, RouteBuilder, Segment
from data.internal.query_domain.expr import Condition
from shared.database import get_database
from shared.orm.route import ContainerOwner, RouteType


async def execute_query(q):
    """Run a built query and return its rows."""
    async with get_database().session_context() as session:
        result = (await session.execute(q)).unique()
    return result.all()


def _connect_segments(
    q: RouteBuilder,
    prev: Segment,
    curr: Segment,
    *,
    custom_conditions: Iterable[Condition] | None = None,
):
    conditions = [prev.end_point.equals(curr.start_point)]
    if custom_conditions:
        conditions.extend(custom_conditions)

    q.add_segment(curr, conditions=conditions)


def _connect_segments_reversed(
    q: RouteBuilder,
    curr: Segment,
    _next: Segment,
    *,
    custom_conditions: Iterable[Condition] | None = None,
):
    conditions = [curr.end_point.equals(_next.start_point)]
    if custom_conditions:
        conditions.extend(custom_conditions)

    q.prepend_segment(curr, conditions=conditions)


def _connect_rail(q: RouteBuilder, prev: Segment):
    rail = Segment(_type=RouteType.RAIL)

    _connect_segments(q, prev, rail, custom_conditions=[
        RouteBuilder.Connector.or_(
            RouteBuilder.Connector.and_(rail.is_through.not_(), prev.is_through.not_()),
            prev.company.equals(rail.company),
        ),
        RouteBuilder.Connector.or_(
            rail.container_owner.equals(ContainerOwner.SOC),
            RouteBuilder.Connector.and_(
                prev.company.equals(rail.company),
                rail.container_owner.equals(ContainerOwner.COC),
            ),
        ),
        RouteBuilder.Connector.or_(
            prev.drop_off_point.null(),
            prev.drop_off_point.equals(rail.end_point),
        ),
    ])
    return rail


def _connect_drop_off(
    q: RouteBuilder,
    prev: Segment,
    curr: Segment,
    container_ids: list[int],
    date: datetime.date,
    drop_off: DropOff,
    *,
    custom_conditions: Iterable[Condition] | None = None,
):
    conditions = [
        curr.start_point.equals(drop_off.start_point),
        curr.end_point.equals(drop_off.end_point),
        drop_off.container.in_(container_ids),
        prev.company.equals(drop_off.company),
        drop_off.effective_from.lte(date),
        drop_off.effective_to.gte(date),
    ]
    if custom_conditions:
        conditions.extend(custom_conditions)

    q.add_drop_off(drop_off, conditions=conditions)


def _require_drop_off_or_drop_off_point(q: RouteBuilder, prev: Segment, drop_off: DropOff):
    q.add_condition(RouteBuilder.Connector.or_(
        prev.drop_off_point.not_null(),
        drop_off.exists(),
    ))


def _build_direct(q: RouteBuilder, core_type: RouteType):
    seg = Segment(_type=core_type)
    q.add_segment(seg)

    q.add_condition(seg.drop_off_point.null())

    return q


def _build_sea_rail(
    q: RouteBuilder,
    container_ids: list[int],
    date: datetime.date,
    *,
    hide_sea_soc: bool = False,
):
    sea = Segment(_type=RouteType.SEA)
    q.add_segment(sea)

    rail = _connect_rail(q, sea)

    drop_off = DropOff()
    _connect_drop_off(q, sea, rail, container_ids, date, drop_off, custom_conditions=[
        sea.drop_off_point.null()
    ])
    _require_drop_off_or_drop_off_point(q, sea, drop_off)

    if hide_sea_soc:
        q.add_condition(sea.container_owner.not_equals(ContainerOwner.SOC))

    return q


# EXPERIMENTAL
# TODO: specify behaviour and login
def _build_rail_sea(q: RouteBuilder):
    rail = Segment(_type=RouteType.RAIL)
    q.add_segment(rail)

    sea = Segment(_type=RouteType.SEA)
    _connect_segments(q, rail, sea)

    return q


def _attach_head_trucks(queries: list, truck_start_point_id: int) -> None:
    for q in queries:
        truck_seg = Segment(_type=RouteType.TRUCK)
        _connect_segments_reversed(
            q, truck_seg, q.get_first_segment(),
            custom_conditions=[truck_seg.start_point.equals(truck_start_point_id)],
        )


def _attach_tail_trucks(queries: list, truck_end_point_id: int) -> None:
    for q in queries:
        truck_seg = Segment(_type=RouteType.TRUCK)
        _connect_segments(
            q, q.get_last_segment(), truck_seg,
            custom_conditions=[truck_seg.end_point.equals(truck_end_point_id)],
        )


def build_queries(
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
    *,
    head_truck: bool,
    tail_truck: bool,
    rail_direct: bool,
    sea_direct: bool,
    sea_rail: bool,
    rail_sea: bool,
    feature_head_truck: bool,
    feature_tail_truck: bool,
    hide_sea_soc: bool = False,
) -> list:
    """Build the queries of the route shapes that are enabled."""
    if head_truck and not feature_head_truck:
        raise ValueError("Can not use 'head_truck' when feature flag 'head-truck' is turned off")
    if tail_truck and not feature_tail_truck:
        raise ValueError("Can not use 'tail_truck' when feature flag 'tail-truck' is turned off")

    base = RouteBuilder(date)
    base.set_containers(container_ids)
    base.set_start_point(start_point_id)
    base.set_end_point(end_point_id)

    queries = []
    if rail_direct:
        queries.append(_build_direct(base.copy(), RouteType.RAIL))
    if sea_direct:
        queries.append(_build_direct(base.copy(), RouteType.SEA))
    if sea_rail:
        builder = base.copy()
        q_sea_rail = _build_sea_rail(
            builder, container_ids, date, hide_sea_soc=hide_sea_soc,
        )
        queries.append(q_sea_rail)
    if rail_sea:
        queries.append(_build_rail_sea(base.copy()))

    if head_truck:
        _attach_head_trucks(queries, start_point_id)

    if tail_truck:
        _attach_tail_trucks(queries, end_point_id)

    return [q.build() for q in queries]
