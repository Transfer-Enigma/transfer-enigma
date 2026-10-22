import datetime
from functools import partial

from data.repositories.points import get_points as load_points
from shared.orm.route import RouteModel, RouteType


async def get_points(*, id_field, date: datetime.date, route_type: RouteType, exclude_route_type: bool = True):
    return await load_points(
        id_field=id_field,
        date=date,
        route_type=route_type,
        exclude_route_type=exclude_route_type,
    )


get_departure_points = partial(get_points, id_field=RouteModel.start_point_id, route_type=RouteType.TRUCK)
get_destination_points = partial(get_points, id_field=RouteModel.end_point_id, route_type=RouteType.TRUCK)

get_truck_departure_points = partial(
    get_points,
    id_field=RouteModel.start_point_id,
    route_type=RouteType.TRUCK,
    exclude_route_type=False,
)
get_truck_destination_points = partial(
    get_points,
    id_field=RouteModel.end_point_id,
    route_type=RouteType.TRUCK,
    exclude_route_type=False,
)
