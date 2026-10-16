import datetime
import logging

from module_data_internal.aggregators.transformers.routes import (
    _segment_from_orm,
    _services_from_segment,
)
from module_shared.database import get_database
from module_shared.models.route import DropItem, RouteResult
from module_shared.schemas.drop import DropModel
from module_shared.schemas.route import PriceModel, RouteModel, RouteType, ServicePriceModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class RouteLinkNotFoundError(Exception):
    """Raised when segments/services from a route link do not form a valid route."""


def parse_link_ids(raw: str | None) -> list[int]:
    """Parse a comma-separated id list from a route link query param."""
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            raise RouteLinkNotFoundError(f"Invalid id: {part!r}") from None
    return ids


def _check_chain(models: list[RouteModel]) -> None:
    for prev, curr in zip(models, models[1:]):
        if prev.end_point_id != curr.start_point_id:
            raise RouteLinkNotFoundError(
                f"Segments {prev.id} and {curr.id} are not connected: "
                f"{prev.end_point_id} != {curr.start_point_id}"
            )


async def _resolve_drop(sea: RouteModel, rail: RouteModel):
    async with get_database().session_context() as session:
        result = await session.execute(
            select(DropModel)
            .where(
                DropModel.company_id == sea.company_id,
                DropModel.start_point_id == rail.start_point_id,
                DropModel.end_point_id == rail.end_point_id,
            )
            .limit(1)
        )
        return result.scalars().first()


async def _load_segments(segment_ids: list[int]) -> list[RouteModel]:
    async with get_database().session_context() as session:
        result = await session.execute(
            select(RouteModel)
            .where(RouteModel.id.in_(segment_ids))
            .options(
                selectinload(RouteModel.company),
                selectinload(RouteModel.start_point),
                selectinload(RouteModel.end_point),
                selectinload(RouteModel.prices).selectinload(PriceModel.container),
                selectinload(RouteModel.services).selectinload(ServicePriceModel.service),
            )
        )
        found = list(result.scalars().all())

    by_id = {m.id: m for m in found}
    missing = [i for i in segment_ids if i not in by_id]
    if missing:
        raise RouteLinkNotFoundError(f"Segments not found: {missing}")

    return [by_id[i] for i in segment_ids]


async def _validate_services(service_ids: list[int], segment_ids: list[int]) -> set[int]:
    """Check requested services exist and belong to the selected segments."""
    if not service_ids:
        return set()

    if len(set(service_ids)) != len(service_ids):
        raise RouteLinkNotFoundError("Duplicate service ids")

    async with get_database().session_context() as session:
        sp_result = await session.execute(
            select(ServicePriceModel)
            .where(ServicePriceModel.id.in_(service_ids))
            .options(selectinload(ServicePriceModel.service))
        )
        found_services = list(sp_result.scalars().all())

    sp_by_id = {sp.id: sp for sp in found_services}
    missing_services = [i for i in service_ids if i not in sp_by_id]
    if missing_services:
        raise RouteLinkNotFoundError(f"Services not found: {missing_services}")

    segment_id_set = set(segment_ids)
    for sp in found_services:
        if sp.route_id not in segment_id_set:
            raise RouteLinkNotFoundError(
                f"Service {sp.id} does not belong to segments {segment_ids}"
            )
    return set(service_ids)


def _is_expired(model: RouteModel, today: datetime.date) -> bool:
    effective_to = model.effective_to
    effective_date = effective_to.date() if isinstance(effective_to, datetime.datetime) else effective_to
    return effective_date < today


async def get_route_by_link(segment_ids: list[int], service_ids: list[int]) -> RouteResult:
    """Build a RouteResult from explicit segment/service ids.

    Raises RouteLinkNotFoundError if a segment is missing, segments do not
    chain via end_point == start_point, a service is missing, or a service
    does not belong to one of the selected segments.
    """
    if not segment_ids:
        raise RouteLinkNotFoundError("No segments specified")

    if len(set(segment_ids)) != len(segment_ids):
        raise RouteLinkNotFoundError("Duplicate segment ids")

    ordered = await _load_segments(segment_ids)
    _check_chain(ordered)
    included_services = await _validate_services(service_ids, segment_ids)

    segments = [_segment_from_orm(m) for m in ordered]

    services = []
    for model, segment in zip(ordered, segments):
        for item in _services_from_segment(model, segment.id):
            item.checked = item.mandatory or (item.id in included_services)
            services.append(item)

    today = datetime.date.today()
    may_be_invalid = any(_is_expired(model, today) for model in ordered)

    drop: DropItem | None = None
    if len(ordered) == 2 and ordered[0].type == RouteType.SEA and ordered[1].type == RouteType.RAIL:
        drop_model = await _resolve_drop(ordered[0], ordered[1])
        if drop_model is not None:
            drop = DropItem(
                price=drop_model.price,
                conversation_percents=drop_model.conversation_percents,
                currency=drop_model.currency,
            )

    logger.info(
        "Route link resolved: segments=%s services=%s drop=%s",
        segment_ids, sorted(included_services), drop is not None,
    )
    return RouteResult(
        segments=segments,
        drop=drop,
        may_be_invalid=may_be_invalid,
        services=services,
    )
