from dataclasses import dataclass, field

from module_data_internal.query_domain.filters import Filter
from module_data_internal.schemas import RouteType


@dataclass
class RouteSegment:
    """Route segment definition (rail or sea)."""

    route_type: RouteType
    _filters: list[Filter] = field(default_factory=list)
    _container_ids: list[int] = field(default_factory=list)

    def add_filter(self, f: Filter | None) -> RouteSegment:
        """Add filter (ignore None for conditional filters)."""
        if f is not None:
            self._filters.append(f)
        return self

    def with_containers(self, ids: list[int]) -> RouteSegment:
        self._container_ids = ids
        return self
