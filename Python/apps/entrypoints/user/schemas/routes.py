from pydantic import BaseModel
from shared.models.route_entities import DropItem, RouteResult, RouteSegment, ServiceItem

from .errors import RouteError

# FIXME: swagger shows this as tuple[null x4]
#   Update FastAPI after fix #10400 issue
NormalizedRoutes = list[tuple[list[RouteSegment], DropItem | None, bool, list[ServiceItem]]]


def normalize_routes(routes: list[RouteResult]) -> NormalizedRoutes:
    return [(r.segments, r.drop, r.may_be_invalid, r.services) for r in routes]


class RoutesDataResponse(BaseModel):
    errors: list[RouteError]
    routes: NormalizedRoutes
