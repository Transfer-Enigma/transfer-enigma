import asyncio
import datetime
import logging
from collections.abc import Iterable

from backend_user.schemas.errors import RouteError
from backend_user.schemas.form_requests import CalculateFormRequest
from backend_user.schemas.routes import NormalizedRoutes
from module_data_fesco_api_adapter import api_client
from module_data_internal import aggregators
from module_shared.config import get_settings as get_shared_settings
from module_shared.models.route import Route

logger = logging.getLogger(__name__)


def _strip_demo_fields(routes: NormalizedRoutes) -> None:
    excluded_fields = get_shared_settings().DEMO_EXCLUDED_FIELDS

    for route in routes:
        segments = route[0]
        for segment in segments:
            for field in excluded_fields:
                setattr(segment, field, None)


async def _get_routes(
    modul,
    date: datetime.date,
    departure: str | int,
    destination: str | int,
    container_weight: float,
    container_type: int,
) -> Iterable[Route]:
    containers = await modul.get_containers(date, departure, destination)
    container_ids = modul.search_container_ids(
        containers,
        container_weight,
        container_type,
    )
    if not container_ids:
        logger.warning("No matching containers for %s-%s", departure, destination)
        return []
    return await modul.find_all_paths(date, departure, destination, container_ids)


def _build_calculation_coros(request: CalculateFormRequest):
    internal_coros = [
        _get_routes(
            aggregators,
            request.dispatchDate,
            departure_id,
            destination_id,
            request.cargoWeight,
            request.containerType,
        )
        for destination_id in request.destinationInternalIds
        for departure_id in request.departureInternalIds
    ]
    external_coros = [
        _get_routes(
            api_client,
            request.dispatchDate,
            departure_id,
            destination_id,
            request.cargoWeight,
            request.containerType,
        )
        for destination_id in request.destinationExternalIds
        for departure_id in request.departureExternalIds
    ]
    return internal_coros, external_coros


async def calculate_routes(request: CalculateFormRequest) -> tuple[list[Route], list[RouteError]]:
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

    routes: list[Route] = []
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
