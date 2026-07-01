import asyncio
import datetime
import logging

from module_data_internal.aggregators.rules import CocSocRule, DropAwareConnection, ThroughRule
from module_data_internal.query_domain import QueryCompiler, RouteSegment, RouteSegmentConnection
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
from module_data_internal.query_domain.segment import RouteSegment as _RS
from module_data_internal.schemas import ContainerOwner, RouteModel, RouteType
from module_shared.cache_settings import get_setting_cached
from module_shared.database import Base, get_database
from module_shared.models.route import RouteResult

from .transformers.routes import transform_routes

logger = logging.getLogger(__name__)


# ── route templates ───────────────────────────────────────────────────


def _base_segment(route_type: RouteType) -> _RS:
    return (
        _RS(route_type)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
        .add_filter(AtEndPoint())
        .add_filter(NoDropOff())
    )


def _rail_direct() -> Route:
    return Route(segments=[_base_segment(RouteType.RAIL)], connections=[])


def _sea_direct() -> Route:
    return Route(segments=[_base_segment(RouteType.SEA)], connections=[])


def _auto_direct() -> Route:
    return Route(segments=[_base_segment(RouteType.AUTO)], connections=[])


def _sea_rail_drop(bridge: DropAwareConnection) -> DropConnection:
    return (
        DropConnection(bridge=bridge, required=False)
        .rule(DropMatchesEndpoint())
        .rule(DropMatchesCompany())
        .rule(DropMatchesContainer())
        .rule(DropEffectiveOn())
    )


def _sea_rail_combined(hide_soc: bool = False) -> Route:
    soc_filter = ExcludeOwners([ContainerOwner.SOC]) if hide_soc else None
    sea = (
        RouteSegment(RouteType.SEA)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
        .add_filter(soc_filter)
    )
    rail = (
        RouteSegment(RouteType.RAIL)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    bridge = DropAwareConnection()
    return Route(
        segments=[sea, rail],
        connections=[
            RouteSegmentConnection(from_seg=sea, to_seg=rail)
            .with_drop_aware_bridge(bridge)
            .rule(CocSocRule())
            .rule(ThroughRule())
            .with_drop(_sea_rail_drop(bridge)),
        ],
    )


def _auto_rail_combined() -> Route:
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
        connections=[
            RouteSegmentConnection(from_seg=auto, to_seg=rail).rule(MatchesEndpoint()),
        ],
    )


def _rail_auto_combined() -> Route:
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
        connections=[
            RouteSegmentConnection(from_seg=rail, to_seg=auto).rule(MatchesEndpoint()),
        ],
    )


def _auto_rail_auto_combined() -> Route:
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


def _auto_sea_rail_auto_combined(hide_soc: bool = False) -> Route:
    soc_filter = ExcludeOwners([ContainerOwner.SOC]) if hide_soc else None
    auto1 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    sea = (
        RouteSegment(RouteType.SEA)
        .add_filter(EffectiveOn())
        .add_filter(soc_filter)
    )
    rail = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
    auto2 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    bridge = DropAwareConnection()
    return Route(
        segments=[auto1, sea, rail, auto2],
        connections=[
            RouteSegmentConnection(from_seg=auto1, to_seg=sea).rule(MatchesEndpoint()),
            RouteSegmentConnection(from_seg=sea, to_seg=rail)
            .with_drop_aware_bridge(bridge)
            .rule(CocSocRule())
            .rule(ThroughRule())
            .with_drop(_sea_rail_drop(bridge)),
            RouteSegmentConnection(from_seg=rail, to_seg=auto2).rule(MatchesEndpoint()),
        ],
    )


def _rail_sea_combined() -> Route:
    rail = (
        RouteSegment(RouteType.RAIL)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    sea = (
        RouteSegment(RouteType.SEA)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    return Route(
        segments=[rail, sea],
        connections=[
            RouteSegmentConnection(from_seg=rail, to_seg=sea).rule(MatchesEndpoint()),
        ],
    )


def _auto_rail_sea_auto_combined() -> Route:
    auto1 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    rail = RouteSegment(RouteType.RAIL).add_filter(EffectiveOn())
    sea = RouteSegment(RouteType.SEA).add_filter(EffectiveOn())
    auto2 = (
        RouteSegment(RouteType.AUTO)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    return Route(
        segments=[auto1, rail, sea, auto2],
        connections=[
            RouteSegmentConnection(from_seg=auto1, to_seg=rail).rule(MatchesEndpoint()),
            RouteSegmentConnection(from_seg=rail, to_seg=sea).rule(MatchesEndpoint()),
            RouteSegmentConnection(from_seg=sea, to_seg=auto2).rule(MatchesEndpoint()),
        ],
    )


# ── pre-compiled queries ──────────────────────────────────────────────

_rail_direct_compiler = QueryCompiler(_rail_direct())
_sea_direct_compiler = QueryCompiler(_sea_direct())
_auto_direct_compiler = QueryCompiler(_auto_direct())
_sea_rail_compiler = QueryCompiler(_sea_rail_combined(hide_soc=False))
_sea_rail_no_soc_compiler = QueryCompiler(_sea_rail_combined(hide_soc=True))
_auto_rail_compiler = QueryCompiler(_auto_rail_combined())
_rail_auto_compiler = QueryCompiler(_rail_auto_combined())
_auto_rail_auto_compiler = QueryCompiler(_auto_rail_auto_combined())
_auto_sea_rail_auto_compiler = QueryCompiler(_auto_sea_rail_auto_combined(hide_soc=False))
_auto_sea_rail_auto_no_soc_compiler = QueryCompiler(_auto_sea_rail_auto_combined(hide_soc=True))
_rail_sea_compiler = QueryCompiler(_rail_sea_combined())
_auto_rail_sea_auto_compiler = QueryCompiler(_auto_rail_sea_auto_combined())


# ── helpers ───────────────────────────────────────────────────────────


async def _execute_query(q):
    async with get_database().session_context() as session:
        result = (await session.execute(q)).unique()
    return result.all()


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

            segments_only = [r for r in row if isinstance(r, RouteModel)]

            ids = tuple(segment.id for segment in segments_only)

            if ids in seen_ids:
                continue

            may_route_be_invalid = False
            for segment in segments_only:
                segment.services = [
                    service for service in segment.services
                    if service.container_id is None or service.container_id in container_ids
                ]

                if segment.effective_to.date() < date:
                    may_route_be_invalid = True
                    break

            seen_ids.add(ids)
            flat_result.append((list(row), may_route_be_invalid))

    return flat_result


async def find_all_paths(
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
) -> list[RouteResult]:
    hide_sea_soc = False
    try:
        async with get_database().session_context() as session:
            setting = await get_setting_cached(session, "feature-flag", "hide-sea-soc")
            if setting is not None:
                hide_sea_soc = bool(setting.value)
    except Exception:
        logger.warning("Failed to read hide-sea-soc setting, defaulting to False")

    sea_rail = _sea_rail_no_soc_compiler if hide_sea_soc else _sea_rail_compiler
    auto_sea_rail = _auto_sea_rail_auto_no_soc_compiler if hide_sea_soc else _auto_sea_rail_auto_compiler

    all_queries = [
        _rail_direct_compiler.build(date, start_point_id, end_point_id, container_ids),
        _sea_direct_compiler.build(date, start_point_id, end_point_id, container_ids),
        sea_rail.build(date, start_point_id, end_point_id, container_ids),
        _auto_direct_compiler.build(date, start_point_id, end_point_id, container_ids),
        _auto_rail_compiler.build(date, start_point_id, end_point_id, container_ids),
        _rail_auto_compiler.build(date, start_point_id, end_point_id, container_ids),
        _auto_rail_auto_compiler.build(date, start_point_id, end_point_id, container_ids),
        auto_sea_rail.build(date, start_point_id, end_point_id, container_ids),
        _rail_sea_compiler.build(date, start_point_id, end_point_id, container_ids),
        _auto_rail_sea_auto_compiler.build(date, start_point_id, end_point_id, container_ids),
    ]

    coroutines = [_execute_query(query) for query in all_queries]
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    return transform_routes(process_results(results, date, container_ids))
