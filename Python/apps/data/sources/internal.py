import datetime

from data.internal.aggregators import containers as internal_containers
from data.internal.aggregators import points as internal_points
from data.internal.aggregators import routes as internal_routes
from data.internal.aggregators.transformers.points import transform_points
from data.protocols import ContainerQuery, PointItem, RouteQuery
from shared.dto.route import ContainerItem, RouteResult
from shared.identifiers import InternalId, RouteIdentifier, SourceKind


def _internal_id(identifier: RouteIdentifier) -> int:
    """The value of an identifier of our own database."""
    if not isinstance(identifier, InternalId):
        raise ValueError(f"Expected an internal id, got {identifier!r}")
    return identifier.value


class InternalSource:
    """The routes, points and containers of our own database."""

    kind = SourceKind.INTERNAL

    async def get_containers(self, query: ContainerQuery) -> list[ContainerItem]:
        return await internal_containers.get_containers(
            query.date,
            str(query.departure),
            str(query.destination),
        )

    async def find_paths(self, query: RouteQuery) -> list[RouteResult]:
        return await internal_routes.find_all_paths(
            query.date,
            _internal_id(query.departure),
            _internal_id(query.destination),
            [_internal_id(container) for container in query.container_ids],
            head_truck=query.head_truck,
            tail_truck=query.tail_truck,
        )

    async def get_departure_points(
        self,
        date: datetime.date,
        *,
        include_truck: bool = False,
    ) -> list[PointItem]:
        if include_truck:
            rows = await internal_points.get_truck_departure_points(date=date)
        else:
            rows = await internal_points.get_departure_points(date=date)
        return list(transform_points(rows))

    async def get_destination_points(
        self,
        date: datetime.date,
        departure: RouteIdentifier | None = None,
        *,
        include_truck: bool = False,
    ) -> list[PointItem]:
        if include_truck:
            rows = await internal_points.get_truck_destination_points(date=date)
        else:
            rows = await internal_points.get_destination_points(date=date)
        return list(transform_points(rows))
