import datetime
from functools import partial

from module_data_internal.schemas import CompanyModel, PointModel, RouteModel
from module_shared.database import get_database
from sqlalchemy import and_, select


def _build_stmt(id_field, date: datetime.date):
    return (
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


async def get_points(*, id_field, date: datetime.date):
    stmt = _build_stmt(id_field, date)
    async with get_database().session_context() as session:
        response = await session.execute(stmt)

    return response.all()


get_departure_points = partial(get_points, id_field=RouteModel.start_point_id)
get_destination_points = partial(get_points, id_field=RouteModel.end_point_id)
