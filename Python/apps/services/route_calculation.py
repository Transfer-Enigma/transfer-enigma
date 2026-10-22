import asyncio
import datetime
import logging
from collections.abc import Iterable
from typing import Protocol

from data.protocols import (
    ContainerQuery,
    ContainerSource,
    RouteQuery,
    RouteSource,
    get_fesco_source,
    get_internal_source,
)
from entrypoints.user.schemas.errors import RouteError
from entrypoints.user.schemas.form_requests import CalculateFormRequest
from entrypoints.user.schemas.routes import NormalizedRoutes
from shared.dto.route import ContainerItem, RouteResult
from shared.identifiers import ExternalId, InternalId, RouteIdentifier

logger = logging.getLogger(__name__)


def _source_id(value: int | str) -> RouteIdentifier:
    """Wrap a raw departure/destination id as the identifier of its source."""
    return InternalId(value) if isinstance(value, int) else ExternalId(str(value))


class _RouteContainerSource(ContainerSource, RouteSource, Protocol):
    """A source that can list containers and find routes."""

    def search_container_ids(
        self, containers: list[ContainerItem], weight: float, container_type: int
    ) -> list:
        ...


def _strip_demo_fields(routes: NormalizedRoutes, excluded_fields: Iterable[str] | None = None) -> None:
    if excluded_fields is None:
        return

    for route in routes:
        segments = route[0]
        for segment in segments:
            for field in excluded_fields:
                setattr(segment, field, None)


async def _get_routes(
    source: _RouteContainerSource,
    date: datetime.date,
    departure: int | str,
    destination: int | str,
    container_weight: float,
    container_type: int,
    *,
    head_truck: bool = False,
    tail_truck: bool = False,
) -> Iterable[RouteResult]:
    dep = _source_id(departure)
    dest = _source_id(destination)
    containers = await source.get_containers(ContainerQuery(date, dep, dest))
    container_ids = source.search_container_ids(containers, container_weight, container_type)
    if not container_ids:
        logger.warning("No matching containers for %s-%s", departure, destination)
        return []
    return await source.find_paths(
        RouteQuery(date, dep, dest, container_ids, head_truck=head_truck, tail_truck=tail_truck)
    )


def _build_calculation_coros(request: CalculateFormRequest):
    head_truck = request.headTruck
    tail_truck = request.tailTruck

    internal_source = get_internal_source()
    external_source = get_fesco_source()

    internal_coros = [
        _get_routes(
            internal_source,
            request.dispatchDate,
            departure_id,
            destination_id,
            request.cargoWeight,
            request.containerType,
            head_truck=head_truck,
            tail_truck=tail_truck,
        )
        for destination_id in request.destinationInternalIds
        for departure_id in request.departureInternalIds
    ]
    external_coros = [
        _get_routes(
            external_source,
            request.dispatchDate,
            departure_id,
            destination_id,
            request.cargoWeight,
            request.containerType,
            head_truck=head_truck,
            tail_truck=tail_truck,
        )
        for destination_id in request.destinationExternalIds
        for departure_id in request.departureExternalIds
    ]
    return internal_coros, external_coros


async def calculate_routes(request: CalculateFormRequest) -> tuple[list[RouteResult], list[RouteError]]:
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


async def calculate_routes_stream(request: CalculateFormRequest):
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
