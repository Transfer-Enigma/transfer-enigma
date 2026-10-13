from module_shared.models.route import DropItem, RouteSegment, ServiceItem
from pydantic import BaseModel

from .errors import RouteError

# FIXME: swagger shows this as tuple[null x4]
#   Update FastAPI after fix #10400 issue
NormalizedRoutes = list[tuple[list[RouteSegment], DropItem | None, bool, list[ServiceItem]]]


class RoutesDataResponse(BaseModel):
    errors: list[RouteError]
    routes: NormalizedRoutes
