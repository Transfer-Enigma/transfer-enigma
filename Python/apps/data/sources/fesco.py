import datetime

from data.fesco import api_client
from data.fesco.api_client.transformers.points import transform_points
from data.protocols import ContainerQuery, PointItem, RouteQuery
from shared.dto.route import ContainerItem, RouteResult
from shared.identifiers import ExternalId, RouteIdentifier, SourceKind


def _external_id(identifier: RouteIdentifier) -> str:
    """The value of an identifier of an external source."""
    if not isinstance(identifier, ExternalId):
        raise ValueError(f"Expected an external id, got {identifier!r}")
    return identifier.value


class FescoSource:
    """The routes, points and containers of the FESCO API."""

    kind = SourceKind.EXTERNAL

    async def get_containers(self, query: ContainerQuery) -> list[ContainerItem]:
        return await api_client.get_containers(
            query.date,
            _external_id(query.departure),
            _external_id(query.destination),
        )

    async def find_paths(self, query: RouteQuery) -> list[RouteResult]:
        routes = await api_client.find_all_paths(
            query.date,
            _external_id(query.departure),
            _external_id(query.destination),
            [_external_id(container) for container in query.container_ids],
            head_truck=query.head_truck,
            tail_truck=query.tail_truck,
        )
        return list(routes)

    async def get_departure_points(
        self,
        date: datetime.date,
        *,
        include_truck: bool = False,
    ) -> list[PointItem]:
        points = await api_client.get_departure_points_by_date(date)
        return list(transform_points(points))

    async def get_destination_points(
        self,
        date: datetime.date,
        departure: RouteIdentifier | None = None,
        *,
        include_truck: bool = False,
    ) -> list[PointItem]:
        if departure is None:
            raise ValueError("The FESCO source needs the departure to find the destinations")
        points = await api_client.get_destination_points_by_date(date, _external_id(departure))
        return list(transform_points(points))
