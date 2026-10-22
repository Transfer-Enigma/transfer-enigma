import datetime
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Query

from entrypoints.user.dependencies.auth_context import bind_caller_context
from entrypoints.user.schemas.get_points_responses import PointsDataResponse
from services.demo_transforms import strip_demo_fields_from_points
from services.points import (
    get_departure_points,
    get_destination_points,
    get_truck_departure_points,
    get_truck_destination_points,
)
from shared.context import CallerContext
from shared.dto.errors import RouteError

router = APIRouter(prefix="/v2/points", tags=["v2", "points"])


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
async def all_departure_by_date(date: datetime.date, context: Annotated[CallerContext, Depends(bind_caller_context)]):
    result, errors = await get_departure_points(date)
    strip_demo_fields_from_points(result, context)

    return {
        "errors": errors,
        "data": result,
    }


@router.get("/destinations", response_model=PointsDataResponse)
async def all_destination_by_date(
    date: datetime.date,
    departure_point_ids: Annotated[tuple[list[int], list[str]], Depends(_parse_point_ids)],
    context: Annotated[CallerContext, Depends(bind_caller_context)],
):
    _, external_point_ids = departure_point_ids

    result, errors = await get_destination_points(date, external_point_ids)
    strip_demo_fields_from_points(result, context)

    return {
        "errors": errors,
        "data": result,
    }


@router.get("/truck-departures", response_model=PointsDataResponse)
async def truck_departure_points(date: datetime.date, context: Annotated[CallerContext, Depends(bind_caller_context)]):
    try:
        result = await get_truck_departure_points(date)
    except Exception as ex:
        return {
            "errors": [RouteError(error_type=str(type(ex)), error_text=str(ex), source="internal")],
            "data": [],
        }

    strip_demo_fields_from_points(result, context)

    return {
        "errors": [],
        "data": result,
    }


@router.get("/truck-destinations", response_model=PointsDataResponse)
async def truck_destination_points(
    date: datetime.date,
    context: Annotated[CallerContext, Depends(bind_caller_context)],
):
    try:
        result = await get_truck_destination_points(date)
    except Exception as ex:
        return {
            "errors": [RouteError(error_type=str(type(ex)), error_text=str(ex), source="internal")],
            "data": [],
        }

    strip_demo_fields_from_points(result, context)

    return {
        "errors": [],
        "data": result,
    }
