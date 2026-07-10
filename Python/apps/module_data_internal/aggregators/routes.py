import asyncio
import datetime
import logging

from module_data_internal.query_domain import DropOff, RouteBuilder, Segment
from module_data_internal.schemas import ContainerOwner, DropModel, RouteModel, RouteType
from module_shared.cache_settings import get_setting_cached
from module_shared.database import Base, get_database
from module_shared.models.route import RouteResult

from .transformers.routes import transform_routes

logger = logging.getLogger(__name__)


async def _execute_query(q):
    async with get_database().session_context() as session:
        result = (await session.execute(q)).unique()
    return result.all()


def build_usual_query(
    route_type: RouteType,
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
):
    seg = Segment(_type=route_type)
    builder = RouteBuilder(date)
    builder.set_containers(container_ids)
    builder.set_start_point(start_point_id)
    builder.set_end_point(end_point_id)
    builder.add_segment(seg)
    builder.add_condition(seg.drop_off_point.null())
    return builder.build()


def build_base_sea_rail_query(
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
    hide_sea_soc: bool = False,
):
    sea = Segment(_type=RouteType.SEA)
    rail = Segment(_type=RouteType.RAIL)
    drop = DropOff()

    builder = RouteBuilder(date)
    builder.set_containers(container_ids)
    builder.set_start_point(start_point_id)
    builder.set_end_point(end_point_id)

    builder.add_segment(sea)

    builder.add_segment(rail, conditions=[
        sea.end_point.equals(rail.start_point),
        RouteBuilder.Connector.or_(
            RouteBuilder.Connector.and_(rail.is_through.not_(), sea.is_through.not_()),
            sea.company.equals(rail.company),
        ),
        RouteBuilder.Connector.or_(
            rail.container_owner.equals(ContainerOwner.SOC),
            RouteBuilder.Connector.and_(
                sea.company.equals(rail.company),
                rail.container_owner.equals(ContainerOwner.COC),
            ),
        ),
        RouteBuilder.Connector.or_(
            sea.drop_off_point.null(),
            sea.drop_off_point.equals(rail.end_point),
        ),
    ])

    builder.add_condition(RouteBuilder.Connector.or_(
        sea.drop_off_point.not_null(),
        drop.exists(),
    ))

    builder.add_drop_off(drop, conditions=[
        sea.drop_off_point.null(),
        rail.start_point.equals(drop.start_point),
        rail.end_point.equals(drop.end_point),
        drop.container.in_(container_ids),
        sea.company.equals(drop.company),
        drop.effective_from.lte(date),
        drop.effective_to.gte(date),
    ])

    if hide_sea_soc:
        builder.add_condition(sea.container_owner.not_equals(ContainerOwner.SOC))

    return builder.build()


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

    query_rail = build_usual_query(
        RouteType.RAIL,
        date,
        start_point_id,
        end_point_id,
        container_ids,
    )
    query_sea = build_usual_query(
        RouteType.SEA,
        date,
        start_point_id,
        end_point_id,
        container_ids,
    )

    sea_rail_query = build_base_sea_rail_query(
        date,
        start_point_id,
        end_point_id,
        container_ids,
        hide_sea_soc=hide_sea_soc,
    )

    all_queries = [
        query_rail,
        query_sea,
        sea_rail_query,
    ]

    coroutines = [_execute_query(query) for query in all_queries]
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    return transform_routes(process_results(results, date, container_ids))
