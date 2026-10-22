from pydantic import BaseModel
from shared.dto.errors import RouteError
from shared.dto.route import DropItem, RouteSegment, ServiceItem

# FIXME: swagger shows this as tuple[null x4]
#   Update FastAPI after fix #10400 issue
NormalizedRoutes = list[tuple[list[RouteSegment], DropItem | None, bool, list[ServiceItem]]]


class RoutesDataResponse(BaseModel):
    errors: list[RouteError]
    routes: NormalizedRoutes
