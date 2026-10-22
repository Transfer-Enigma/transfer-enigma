"""Internal database as a data source."""

from data.internal import aggregators
from data.protocols import ContainerQuery, ContainerSource, PointSource, RouteQuery, RouteSource
from shared.dto.point import PointItem
from shared.dto.route import ContainerItem
from shared.identifiers import InternalId, RouteIdentifier, SourceKind


def _internal_id(identifier: RouteIdentifier) -> int:
    if not isinstance(identifier, InternalId):
        raise TypeError(f"expected InternalId, got {type(identifier)!r}")
    return identifier.value


class InternalSource(ContainerSource, RouteSource, PointSource):
    """Our own database as a data source."""

    kind = SourceKind.INTERNAL

    async def get_containers(self, query: ContainerQuery) -> list[ContainerItem]:
        return await aggregators.get_containers(
            query.date,
            _internal_id(query.departure),
            _internal_id(query.destination),
        )

    def search_container_ids(
        self, containers: list[ContainerItem], weight: float, container_type: int
    ) -> list:
        return aggregators.search_container_ids(containers, weight, container_type)

    async def find_paths(self, query: RouteQuery) -> list:
        container_ids = [_internal_id(c) for c in query.container_ids]
        return await aggregators.find_all_paths(
            query.date,
            _internal_id(query.departure),
            _internal_id(query.destination),
            container_ids,
            head_truck=query.head_truck,
            tail_truck=query.tail_truck,
        )

    async def get_departure_points(self, date) -> list[PointItem]:
        return await aggregators.get_departure_points(date=date)

    async def get_destination_points(
        self, date, departure: RouteIdentifier
    ) -> list[PointItem]:
        return await aggregators.get_destination_points(date=date, departure=departure)
