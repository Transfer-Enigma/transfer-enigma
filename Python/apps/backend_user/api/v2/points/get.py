import asyncio
import datetime
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Query
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from backend_user.dependencies.auth_context import AuthContext, get_auth_context
from backend_user.schemas.errors import RouteError
from backend_user.schemas.get_points_responses import PointsDataResponse
from backend_user.utils.group_points import group_companies, group_transfers, raw_point_from_dict
from module_data_fesco_api_adapter import api_client
from module_data_fesco_api_adapter.api_client.transformers.points import (
    transform_points as map_fesco,
)
from module_data_internal import aggregators
from module_data_internal.aggregators.transformers.points import transform_points as map_custom
from module_data_internal.schemas import CompanyModel, PointModel
from module_shared.cache_settings import get_setting_cached
from module_shared.database import get_database

router = APIRouter(prefix="/v2/points", tags=["v2", "points"])


def _strip_demo_fields_from_points(data: list, auth: AuthContext, excluded_fields: list[str] | None = None) -> None:
    if not auth.is_demo:
        return

    if excluded_fields is None or "company" not in excluded_fields:
        return

    for point in data:
        point.companies = []
        for port in point.ports:
            port.companies = []


def _parse_point_ids(departure_point_ids: Annotated[str, Query]) -> tuple[list[int], list[str]]:
    if not departure_point_ids:
        return [], []

    internal_point_ids: list[int] = []
    external_point_ids: list[str] = []
    for encoded_point_id in departure_point_ids.split(","):
        if encoded_point_id[0] == "E":
            external_point_ids.append(encoded_point_id[1:])
        else:
            internal_point_ids.append(int(encoded_point_id[1:]))

    return internal_point_ids, external_point_ids


@router.get("/departures", response_model=PointsDataResponse)
async def all_departure_by_date(date: datetime.date, auth: Annotated[AuthContext, Depends(get_auth_context)]):
    fesco_points: Iterator[dict[str, Any]]
    custom_points: list[tuple[PointModel, CompanyModel]]

    fesco_points, custom_points = await asyncio.gather(
        api_client.get_departure_points_by_date(date),
        aggregators.get_departure_points(date=date),
        return_exceptions=True,
    )

    errors = []
    data: list[dict[str, Any]] = []

    if isinstance(fesco_points, BaseException):
        errors.append(RouteError(error_type=str(type(fesco_points)), error_text=str(fesco_points), source="external"))
    else:
        data.extend(map_fesco(fesco_points))

    if isinstance(custom_points, BaseException):
        errors.append(RouteError(error_type=str(type(custom_points)), error_text=str(custom_points), source="internal"))
    else:
        data.extend(map_custom(custom_points))

    result = group_transfers(group_companies([raw_point_from_dict(point) for point in data], {"FESCO"}), {"FESCO"})
    async with get_database().session_context() as session:
        setting = await get_setting_cached(session, "feature-flag", "demo-excluded-fields")
        excluded_fields = setting.value if setting and isinstance(setting.value, list) else []
    _strip_demo_fields_from_points(result, auth, excluded_fields)

    return {
        "errors": errors,
        "data": result,
    }


@router.get("/destinations", response_model=PointsDataResponse)
async def all_destination_by_date(
    date: datetime.date,
    departure_point_ids: Annotated[tuple[list[int], list[str]], Depends(_parse_point_ids)],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
):
    coros = [aggregators.get_destination_points(date=date)]

    _, external_point_ids = departure_point_ids

    for point_id in external_point_ids:
        coros.append(api_client.get_destination_points_by_date(date, point_id))

    results = await asyncio.gather(
        *coros,
        return_exceptions=True,
    )

    errors = []
    data: list[dict[str, Any]] = []

    if not results:
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, detail="Unknown error: no results")

    fesco_points_array: list[Iterator[dict[str, Any]] | BaseException]
    custom_points, *fesco_points_array = results
    if isinstance(custom_points, BaseException):
        errors.append(RouteError(error_type=str(type(custom_points)), error_text=str(custom_points), source="internal"))
    else:
        data.extend(map_custom(custom_points))

    for fesco_points in fesco_points_array:
        if isinstance(fesco_points, BaseException):
            errors.append(
                RouteError(error_type=str(type(fesco_points)), error_text=str(fesco_points), source="external")
            )
        else:
            data.extend(map_fesco(fesco_points))

    result = group_transfers(group_companies([raw_point_from_dict(point) for point in data], {"FESCO"}), {"FESCO"})
    async with get_database().session_context() as session:
        setting = await get_setting_cached(session, "feature-flag", "demo-excluded-fields")
        excluded_fields = setting.value if setting and isinstance(setting.value, list) else []
    _strip_demo_fields_from_points(result, auth, excluded_fields)

    return {
        "errors": errors,
        "data": result,
    }
