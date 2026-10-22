import datetime
from typing import Protocol

from shared.dto.point import PointItem
from shared.dto.route import ContainerItem, RouteResult
from shared.identifiers import RouteIdentifier, SourceKind


class ContainerQuery:
    """The containers a source offers for a departure and a destination."""

    def __init__(
        self,
        date: datetime.date,
        departure: RouteIdentifier,
        destination: RouteIdentifier,
    ) -> None:
        self.date = date
        self.departure = departure
        self.destination = destination


class RouteQuery:
    """The routes a source can offer for a departure, a destination and containers."""

    def __init__(
        self,
        date: datetime.date,
        departure: RouteIdentifier,
        destination: RouteIdentifier,
        container_ids: list[RouteIdentifier] | None = None,
        *,
        head_truck: bool = False,
        tail_truck: bool = False,
    ) -> None:
        self.date = date
        self.departure = departure
        self.destination = destination
        self.container_ids = container_ids or []
        self.head_truck = head_truck
        self.tail_truck = tail_truck


class ContainerSource(Protocol):
    """A source of containers."""

    kind: SourceKind

    async def get_containers(self, query: ContainerQuery) -> list[ContainerItem]:
        """The containers the source offers for the query."""
        ...


class RouteSource(Protocol):
    """A source of routes."""

    kind: SourceKind

    async def find_paths(self, query: RouteQuery) -> list[RouteResult]:
        """The routes the source offers for the query."""
        ...


class PointSource(Protocol):
    """A source of points."""

    kind: SourceKind

    async def get_departure_points(
        self,
        date: datetime.date,
        *,
        include_truck: bool = False,
    ) -> list[PointItem]:
        """The points the source can depart from."""
        ...

    async def get_destination_points(
        self,
        date: datetime.date,
        departure: RouteIdentifier | None = None,
        *,
        include_truck: bool = False,
    ) -> list[PointItem]:
        """The points the source can arrive at.

        A source that does not know the departure ignores it.
        """
        ...


def get_internal_source() -> ContainerSource:
    """The internal database as a data source."""
    from data.sources.internal import InternalSource

    return InternalSource()


def get_fesco_source() -> ContainerSource:
    """The FESCO API as a data source."""
    from data.sources.fesco import FescoSource

    return FescoSource()
