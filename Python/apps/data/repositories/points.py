import datetime

from shared.database import get_database
from shared.orm.company import CompanyModel
from shared.orm.point import PointModel
from shared.orm.route import RouteModel, RouteType
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


async def get_points(
    *,
    id_field,
    date: datetime.date,
    route_type: RouteType,
    exclude_route_type: bool = True,
) -> list[tuple[PointModel, CompanyModel]]:
    """The points of the companies that serve the given date."""
    stmt = _build_stmt(id_field, date, route_type, exclude_route_type)
    async with get_database().session_context() as session:
        response = await session.execute(stmt)

    return list(response.all())
