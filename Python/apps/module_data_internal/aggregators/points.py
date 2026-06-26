from functools import partial

from module_data_internal.schemas import CompanyModel, PointModel, RouteSegmentModel
from module_shared.database import get_database
from sqlalchemy import select


def _build_stmt_joined_with_company_by_route(id_field):
    return (
        select(PointModel, CompanyModel).distinct()
        .join(
            RouteSegmentModel,
            id_field == PointModel.id,
        )
        .join(CompanyModel)
    )


async def get_points(*, id_field):
    async with get_database().session_context() as session:
        stmt = _build_stmt_joined_with_company_by_route(id_field)
        response = await session.execute(stmt)

    return response.all()


get_departure_points = partial(get_points, id_field=RouteSegmentModel.start_point_id)
get_destination_points = partial(get_points, id_field=RouteSegmentModel.end_point_id)
