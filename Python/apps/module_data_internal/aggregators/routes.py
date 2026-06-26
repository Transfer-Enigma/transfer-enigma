import asyncio
import datetime
import logging

from module_data_internal.schemas import (
    ContainerOwner,
    DropModel,
    PriceModel,
    RouteModel,
    RouteType,
    ServicePriceModel,
)
from module_shared.cache_settings import get_setting_cached
from module_shared.database import Base, get_database
from module_shared.models.route import Route
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import aliased, contains_eager, joinedload, selectinload

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
    where_clause = and_(
        RouteModel.effective_from <= date,
        RouteModel.effective_to >= date,
        RouteModel.start_point_id == start_point_id,
        RouteModel.end_point_id == end_point_id,
        RouteModel.type == route_type,
        RouteModel.dropp_off_point_id.is_(None),
    )

    return (  # noqa: ECE001
        select(RouteModel)
        .where(where_clause)
        .join(
            PriceModel,
            and_(
                RouteModel.id == PriceModel.route_id,
                PriceModel.container_id.in_(container_ids)
            ),
        )
        .outerjoin(
            ServicePriceModel,
            and_(
                RouteModel.id == ServicePriceModel.route_id,
                or_(
                    ServicePriceModel.container_id.is_(None),
                    ServicePriceModel.container_id.in_(container_ids),
                ),
            ),
        )
        .order_by(desc(RouteModel.effective_to))
        # note: I tried using 'group by' statement, but it cuts off prices
        .options(
            joinedload(RouteModel.start_point),
            joinedload(RouteModel.end_point),
            joinedload(RouteModel.company),
            contains_eager(RouteModel.services).joinedload(ServicePriceModel.service),
            contains_eager(RouteModel.prices).joinedload(PriceModel.container),
        )
    )


def _create_aliases():
    SeaRoute = aliased(RouteModel, name="sea_route")
    RailRoute = aliased(RouteModel, name="rail_route")
    SeaPrice = aliased(PriceModel, name="sea_price")
    RailPrice = aliased(PriceModel, name="rail_price")
    SeaServicePrice = aliased(ServicePriceModel, name="sea_service_price")
    RailServicePrice = aliased(ServicePriceModel, name="rail_service_price")
    return SeaRoute, RailRoute, SeaPrice, RailPrice, SeaServicePrice, RailServicePrice


def build_base_sea_rail_query(
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
    hide_sea_soc: bool = False,
) -> tuple:
    SeaRoute, RailRoute, SeaPrice, RailPrice, SeaServicePrice, RailServicePrice = _create_aliases()
    where_conditions = [
        # Types
        SeaRoute.type == RouteType.SEA,
        RailRoute.type == RouteType.RAIL,
        # Dates
        SeaRoute.effective_from <= date,
        RailRoute.effective_from <= date,
        SeaRoute.effective_to >= date,
        RailRoute.effective_to >= date,
        # Points
        SeaRoute.start_point_id == start_point_id,
        RailRoute.end_point_id == end_point_id,
        # Containers
        SeaPrice.container_id.in_(container_ids),
        RailPrice.container_id.in_(container_ids),
        # COC/SOC logic
        or_(
            RailRoute.container_owner == ContainerOwner.SOC,
            and_(
                SeaRoute.company_id == RailRoute.company_id,
                RailRoute.container_owner == ContainerOwner.COC,
            ),
        ),
        # Through routes logic
        or_(
            ~RailRoute.is_through & ~SeaRoute.is_through,
            SeaRoute.company_id == RailRoute.company_id,
        ),
        # Drop-off must exist: either via dropp_off_point_id or via DROPS table
        or_(
            SeaRoute.dropp_off_point_id.isnot(None),
            DropModel.id.isnot(None),
        ),
    ]
    if hide_sea_soc:
        where_conditions.append(SeaRoute.container_owner != ContainerOwner.SOC)

    drop_join_clause = and_(
        SeaRoute.dropp_off_point_id.is_(None),  # if not, drop is already included!
        # Points
        RailRoute.start_point_id == DropModel.start_point_id,
        RailRoute.end_point_id == DropModel.end_point_id,
        # Container
        RailPrice.container_id == DropModel.container_id,
        # Company
        SeaRoute.company_id == DropModel.company_id,
        # Drop-off must be valid on the shipping date
        DropModel.effective_from <= date,
        DropModel.effective_to >= date,
    )

    return (  # noqa: ECE001
        select(SeaRoute, RailRoute, DropModel)
        .where(and_(*where_conditions))
        .join(SeaPrice, SeaRoute.id == SeaPrice.route_id)
        .join(RailRoute, and_(
            SeaRoute.end_point_id == RailRoute.start_point_id,
            or_(
                SeaRoute.dropp_off_point_id.is_(None),
                SeaRoute.dropp_off_point_id == RailRoute.end_point_id,
            ),
        ))
        .join(RailPrice, RailRoute.id == RailPrice.route_id)
        .outerjoin(DropModel, drop_join_clause)
        .order_by(desc(SeaRoute.effective_to), desc(RailRoute.effective_to))
        # note: I tried using 'group by' statement, but it cuts off prices
        # here could be 'group_by', but it doesn't work correctly with 'joinedload'
        # so we select unique on the client-side
        .options(
            joinedload(SeaRoute.start_point),
            joinedload(SeaRoute.end_point),
            joinedload(SeaRoute.company),
            contains_eager(SeaRoute.prices, alias=SeaPrice).joinedload(PriceModel.container),
            selectinload(SeaRoute.services.of_type(SeaServicePrice)).joinedload(SeaServicePrice.service),
            # note: with_loader_criteria does not work properly with cache (first start - ok, next - ignored)
            # so we need filter it after we've got a response
            # the code:
            # `with_loader_criteria(SeaServicePrice, or_(`
            #     `SeaServicePrice.container_id.is_(None),`
            #     `SeaServicePrice.container_id.in_(container_ids),`
            # `)),`
            joinedload(RailRoute.start_point),
            joinedload(RailRoute.end_point),
            joinedload(RailRoute.company),
            contains_eager(RailRoute.prices, alias=RailPrice).joinedload(PriceModel.container),
            selectinload(RailRoute.services.of_type(RailServicePrice)).joinedload(RailServicePrice.service),
            # note: with_loader_criteria does not work properly with cache (first start - ok, next - ignored)
            # so we need filter it after we've got a response
            # the code:
            # `with_loader_criteria(RailServicePrice, or_(`
            #     `RailServicePrice.container_id.is_(None),`
            #     `RailServicePrice.container_id.in_(container_ids),`
            # `)),`
        )
    )


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
) -> list[Route]:
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
