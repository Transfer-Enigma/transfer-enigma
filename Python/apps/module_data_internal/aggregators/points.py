from functools import partial

from module_data_internal.schemas import CompanyModel, PointModel, RouteModel
from module_shared.database import get_database
from sqlalchemy import select


def _build_stmt_joined_with_company_by_route(id_field):
    return (
        select(PointModel, CompanyModel).distinct()
        .join(
            RouteModel,
            id_field == PointModel.id,
        )
        .join(CompanyModel)
    )


async def get_points(*, id_field):
    stmt = _build_stmt_joined_with_company_by_route(id_field)
    async with get_database().session_context() as session:
        response = await session.execute(stmt)

    return response.all()


get_departure_points = partial(get_points, id_field=RouteModel.start_point_id)
get_destination_points = partial(get_points, id_field=RouteModel.end_point_id)
