from pydantic import BaseModel
<<<<<<< HEAD
from shared.dto.route import DropItem, RouteSegment, ServiceItem
=======
from shared.models.route import DropItem, RouteSegment, ServiceItem
>>>>>>> a90e866f (Python: Rename packages by architecture layer)

from .errors import RouteError

# FIXME: swagger shows this as tuple[null x4]
#   Update FastAPI after fix #10400 issue
NormalizedRoutes = list[tuple[list[RouteSegment], DropItem | None, bool, list[ServiceItem]]]


class RoutesDataResponse(BaseModel):
    errors: list[RouteError]
    routes: NormalizedRoutes
