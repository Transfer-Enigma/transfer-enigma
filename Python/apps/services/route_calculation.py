import asyncio
import datetime
import logging
from collections.abc import Iterable

from data.protocols import ContainerQuery, RouteQuery
from data.sources.fesco import FescoSource
from data.sources.internal import InternalSource
from shared.dto.calculation import CalculationRequest
from shared.dto.errors import RouteError
from shared.dto.route import ContainerItem, RouteResult, RouteSegment
from shared.identifiers import ExternalId, InternalId, RouteIdentifier, SourceKind

logger = logging.getLogger(__name__)

internal_source = InternalSource()
fesco_source = FescoSource()


def search_containers(containers: list[ContainerItem], weight: float, size: int) -> list[ContainerItem]:
    """The containers that fit the weight and the size of the request."""
    matching = []
    for container in containers:
        if container.size != size:
            continue
        weight_from = container.weight_from
        weight_to = container.weight_to
        if weight_to is None:
            matching.append(container)
            continue
        if weight_from is not None and weight_from <= weight <= weight_to:
            matching.append(container)
    return matching


def _make_identifier(kind: SourceKind, value) -> RouteIdentifier:
    """The identifier of a value of a source."""
    if kind == SourceKind.INTERNAL:
        return InternalId(value)
    return ExternalId(value)


def deduplicate_routes(routes: list[RouteResult]) -> list[RouteResult]:
    """Keep the first of the routes that have the same segments."""
    unique: list[RouteResult] = []
    seen: set[tuple[object, ...]] = set()

    for route in routes:
        ids = tuple(segment.id for segment in route.segments)
        if ids in seen:
            continue
        seen.add(ids)
        unique.append(route)

    return unique


def is_expired(segment: RouteSegment, date: datetime.date) -> bool:
    """Whether the segment is not valid anymore at the given date."""
    effective_to = segment.effectiveTo
    if isinstance(effective_to, str):
        try:
            effective_to = datetime.datetime.fromisoformat(effective_to)
        except ValueError:
            return False
    return effective_to.date() < date


def mark_expired_routes(routes: list[RouteResult], date: datetime.date) -> list[RouteResult]:
    """Mark the routes that hold a segment which is not valid anymore."""
    for route in routes:
        route.may_be_invalid = any(is_expired(segment, date) for segment in route.segments)
    return routes


async def _get_routes(
    source,
    date: datetime.date,
    departure: RouteIdentifier,
    destination: RouteIdentifier,
    container_weight: float,
    container_type: int,
    *,
    head_truck: bool = False,
    tail_truck: bool = False,
) -> Iterable[RouteResult]:
    containers = await source.get_containers(ContainerQuery(date, departure, destination))
    matching = search_containers(containers, container_weight, container_type)
    if not matching:
        logger.warning("No matching containers for %s-%s", departure, destination)
        return []
    routes = await source.find_paths(
        RouteQuery(
            date,
            departure,
            destination,
            [_make_identifier(source.kind, container.id) for container in matching],
            head_truck=head_truck,
            tail_truck=tail_truck,
        ),
    )
    return mark_expired_routes(deduplicate_routes(list(routes)), date)


def _build_calculation_coros(request: CalculationRequest):
    head_truck = request.head_truck
    tail_truck = request.tail_truck

    internal_coros = [
        _get_routes(
            internal_source,
            request.dispatch_date,
            InternalId(departure_id),
            InternalId(destination_id),
            request.cargo_weight,
            request.container_type,
            head_truck=head_truck,
            tail_truck=tail_truck,
        )
        for destination_id in request.destination_internal_ids
        for departure_id in request.departure_internal_ids
    ]
    external_coros = [
        _get_routes(
            fesco_source,
            request.dispatch_date,
            ExternalId(departure_id),
            ExternalId(destination_id),
            request.cargo_weight,
            request.container_type,
            head_truck=head_truck,
            tail_truck=tail_truck,
        )
        for destination_id in request.destination_external_ids
        for departure_id in request.departure_external_ids
    ]
    return internal_coros, external_coros


async def calculate_routes(request: CalculationRequest) -> tuple[list[RouteResult], list[RouteError]]:
    internal_coros, external_coros = _build_calculation_coros(request)

    logger.info(
        "Calculating routes: %d internal / %d external pairs",
        len(internal_coros),
        len(external_coros),
    )

    internal_result, external_result = await asyncio.gather(
        asyncio.gather(*internal_coros, return_exceptions=True),
        asyncio.gather(*external_coros, return_exceptions=True),
    )
    result = [(False, i) for i in internal_result] + [(True, i) for i in external_result]

    routes: list[RouteResult] = []
    errors: list[RouteError] = []
    source_map = ("internal", "external")

    for is_external, coro_result in result:
        if isinstance(coro_result, BaseException):
            source = source_map[int(is_external)]
            logger.error("Route %s: calculation failed", source, exc_info=coro_result)
            errors.append(RouteError(
                error_type=str(type(coro_result)),
                error_text=str(coro_result),
                source=source,
            ))
        elif coro_result:
            res = list(coro_result)
            if res:
                routes.extend(res)

    logger.info("Result: %d routes, %d errors", len(routes), len(errors))
    return routes, errors


async def calculate_routes_stream(request: CalculationRequest):
    internal_coros, external_coros = _build_calculation_coros(request)
    source_map = ("internal", "external")

    async def _run_tagged(is_external: bool, coro):
        try:
            result = await coro
            return is_external, result, None
        except Exception as e:
            return is_external, None, e

    tagged = [
        _run_tagged(False, c) for c in internal_coros
    ] + [
        _run_tagged(True, c) for c in external_coros
    ]

    for future in asyncio.as_completed(tagged):
        is_external, result, error = await future
        if error:
            source = source_map[int(is_external)]
            logger.error("Route %s: calculation failed", source, exc_info=error)
            yield RouteError(
                error_type=type(error).__name__,
                error_text=str(error),
                source=source,
            )
        elif result:
            for route in list(result):
                yield route
