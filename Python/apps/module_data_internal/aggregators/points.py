import datetime
from functools import partial

from module_data_internal.schemas import CompanyModel, PointModel, RouteModel, RouteType
from module_shared.database import get_database
from sqlalchemy import and_, select


def _build_stmt(id_field, date: datetime.date, route_type: RouteType, exclude_route_type: bool = True):
    stmt = (
        select(PointModel, CompanyModel).distinct()
        .join(
            RouteModel,
            and_(
                id_field == PointModel.id,
                RouteModel.effective_from <= date,
                RouteModel.effective_to >= date,
            ),
        )
        .join(CompanyModel)
    )
    if exclude_route_type:
        stmt = stmt.where(RouteModel.type != route_type)
    else:
        stmt = stmt.where(RouteModel.type == route_type)
    return stmt


async def get_points(*, id_field, date: datetime.date, route_type: RouteType, exclude_route_type: bool = True):
    stmt = _build_stmt(id_field, date, route_type, exclude_route_type)
    async with get_database().session_context() as session:
        response = await session.execute(stmt)

    return response.all()


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
