import asyncio
import datetime

from data.protocols import PointItem
from data.sources.fesco import FescoSource
from data.sources.internal import InternalSource
from services.group_points import (
    GroupedPointWithPort,
    group_companies,
    group_transfers,
    raw_point_from_dict,
)
from shared.dto.errors import RouteError
from shared.identifiers import ExternalId

internal_source = InternalSource()
fesco_source = FescoSource()


async def _gather(*coros) -> list:
    """Run the coroutines of the sources, keeping the exceptions as results."""
    return await asyncio.gather(*coros, return_exceptions=True)


def _as_error(exception: BaseException, source: str) -> RouteError:
    return RouteError(error_type=str(type(exception)), error_text=str(exception), source=source)


def group_points(points: list[PointItem]) -> list[GroupedPointWithPort]:
    """Group the points of the sources by company and by transfer."""
    raw = [raw_point_from_dict(point) for point in points]
    return group_transfers(group_companies(raw, {"FESCO"}), {"FESCO"})


async def get_departure_points(date: datetime.date) -> tuple[list[GroupedPointWithPort], list[RouteError]]:
    """The points of the departure, and the errors of the sources."""
    external, internal = await _gather(
        fesco_source.get_departure_points(date),
        internal_source.get_departure_points(date),
    )

    errors: list[RouteError] = []
    points: list[PointItem] = []

    if isinstance(external, BaseException):
        errors.append(_as_error(external, "external"))
    else:
        points.extend(external)

    if isinstance(internal, BaseException):
        errors.append(_as_error(internal, "internal"))
    else:
        points.extend(internal)

    return group_points(points), errors


async def get_destination_points(
    date: datetime.date,
    external_departures: list[str],
) -> tuple[list[GroupedPointWithPort], list[RouteError]]:
    """The points of the destination, and the errors of the sources."""
    coros = [internal_source.get_destination_points(date)]
    coros.extend(
        fesco_source.get_destination_points(date, ExternalId(departure))
        for departure in external_departures
    )

    results = await _gather(*coros)

    errors: list[RouteError] = []
    points: list[PointItem] = []

    internal, *external_results = results

    if isinstance(internal, BaseException):
        errors.append(_as_error(internal, "internal"))
    else:
        points.extend(internal)

    for external in external_results:
        if isinstance(external, BaseException):
            errors.append(_as_error(external, "external"))
        else:
            points.extend(external)

    return group_points(points), errors


async def get_truck_departure_points(date: datetime.date) -> list[GroupedPointWithPort]:
    """The points the truck routes depart from."""
    points = await internal_source.get_departure_points(date, include_truck=True)
    return group_points(points)


async def get_truck_destination_points(date: datetime.date) -> list[GroupedPointWithPort]:
    """The points the truck routes arrive at."""
    points = await internal_source.get_destination_points(date, include_truck=True)
    return group_points(points)
