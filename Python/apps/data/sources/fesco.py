"""FESCO API as a data source."""

from data.fesco import api_client
from data.protocols import ContainerQuery, ContainerSource, PointSource, RouteQuery, RouteSource
from shared.dto.point import PointItem
from shared.dto.route import ContainerItem
from shared.identifiers import RouteIdentifier, SourceKind


class FescoSource(ContainerSource, RouteSource, PointSource):
    """The FESCO API as a data source."""

    kind = SourceKind.EXTERNAL

    async def get_containers(self, query: ContainerQuery) -> list[ContainerItem]:
        return await api_client.containers.get_containers(
            query.date,
            str(query.departure),
            str(query.destination),
        )

    def search_container_ids(
        self, containers: list[ContainerItem], weight: float, container_type: int
    ) -> list:
        return api_client.containers.search_container_ids(containers, weight, container_type)

    async def find_paths(self, query: RouteQuery) -> list:
        return list(
            await api_client.routes.find_all_paths(
                query.date,
                str(query.departure),
                str(query.destination),
                [str(c) for c in query.container_ids],
                head_truck=query.head_truck,
                tail_truck=query.tail_truck,
            )
        )

    async def get_departure_points(self, date) -> list[PointItem]:
        return await api_client.points.get_departure_points_by_date(date)

    async def get_destination_points(
        self, date, departure: RouteIdentifier
    ) -> list[PointItem]:
        return await api_client.points.get_destination_points_by_date(
            date, str(departure)
        )
