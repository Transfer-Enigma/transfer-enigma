import asyncio
import datetime
import logging
from collections.abc import Iterable

from module_data_internal.query_domain import DropOff, RouteBuilder, Segment
from module_data_internal.query_domain.expr import Condition
from module_data_internal.schemas import ContainerOwner, DropModel, RouteModel, RouteType
from module_shared.cache_settings import get_setting_cached
from module_shared.database import Base, get_database
from module_shared.models.route import RouteResult
from module_shared.setting_definitions import get_setting_definition

from .transformers.routes import transform_routes

logger = logging.getLogger(__name__)


async def _execute_query(q):
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
    segs = [Segment(_type=core_type)]
    q.add_segment(segs[0])
    q.add_condition(segs[0].drop_off_point.null())
    return [q.build()]


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

    return [q.build()]


# EXPERIMENTAL
# TODO: specify behaviour and login
def _build_rail_sea(q: RouteBuilder):
    rail = Segment(_type=RouteType.RAIL)
    q.add_segment(rail)

    _connect_segments(q, rail, Segment(_type=RouteType.SEA))

    return [q.build()]


def build_queries(
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
    *,
    rail_direct: bool,
    sea_direct: bool,
    sea_rail: bool,
    rail_sea: bool,
    hide_sea_soc: bool = False,
) -> list:
    base = RouteBuilder(date)
    base.set_containers(container_ids)
    base.set_start_point(start_point_id)
    base.set_end_point(end_point_id)

    queries = []
    if rail_direct:
        queries += _build_direct(base.copy(), RouteType.RAIL)
    if sea_direct:
        queries += _build_direct(base.copy(), RouteType.SEA)
    if sea_rail:
        queries += _build_sea_rail(base.copy(), container_ids, date, hide_sea_soc=hide_sea_soc)
    if rail_sea:
        queries += _build_rail_sea(base)
    return queries


def process_results(
    results: list[list[list[Base]] | BaseException],
    date: datetime.date,
    container_ids: list[int],
) -> list[tuple[list[Base], bool]]:
    flat_result: list = []
    seen_ids: set[tuple[int, ...]] = set()

    for result in results:
        if not result or isinstance(result, BaseException):
            if isinstance(result, BaseException):
                logger.error("Route query failed", exc_info=result)
            continue

        for row in result:
            if not row:
                continue

            routes: list[RouteModel] = row[:-1] if not row[-1] or isinstance(row[-1], DropModel) else row

            ids = tuple(segment.id for segment in routes)

            if ids in seen_ids:
                continue

            may_route_be_invalid = False
            for segment in routes:
                # TODO: find another way...
                segment.services = [
                    service for service in segment.services
                    if service.container_id is None or service.container_id in container_ids
                ]

                if segment.effective_to.date() < date:
                    may_route_be_invalid = True
                    break

            seen_ids.add(ids)
            flat_result.append((row, may_route_be_invalid))

    return flat_result


_flags: list[tuple[str, str]] = [
    ("hide-sea-soc", "hide_sea_soc"),
    ("rail-direct", "rail_direct"),
    ("sea-direct", "sea_direct"),
    ("sea-rail", "sea_rail"),
    ("rail-sea", "rail_sea"),
]


async def find_all_paths(
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
) -> list[RouteResult]:
    flag_values: dict[str, bool] = {}

    try:
        async with get_database().session_context() as session:
            for name, local_name in _flags:
                setting = await get_setting_cached(session, "feature-flag", name)
                if setting is None:
                    setting_def = get_setting_definition("feature-flag", name)
                    if not setting_def:
                        raise RuntimeError("Feature flag " + name + " not found")

                    flag_values[local_name] = bool(setting_def.true_type_default)
                else:
                    flag_values[local_name] = bool(setting.value)
    except Exception:
        logger.warning("Failed to read hide-sea-soc setting, defaulting to False\nException info:", exc_info=True)

    all_queries = build_queries(
        date, start_point_id, end_point_id, container_ids,
        **flag_values,
    )

    coroutines = [_execute_query(query) for query in all_queries]
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    return transform_routes(process_results(results, date, container_ids))
