from dataclasses import dataclass, field

from module_data_internal.query_domain.connection import RouteSegmentConnection
from module_data_internal.query_domain.segment import RouteSegment


@dataclass
class Route:
    """Route definition: segments + connections."""

    segments: list[RouteSegment]
    connections: list[RouteSegmentConnection] = field(default_factory=list)
