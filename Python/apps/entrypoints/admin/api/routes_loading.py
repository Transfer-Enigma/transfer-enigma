from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, File
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

import gspread
import pandas
from entrypoints.admin.dependencies.auth import request_auth
from gspread_dataframe import get_as_dataframe
from services.routes_loading.errors_parser import parse_all_warning_types
from services.routes_loading.fields_map import get_fields_config_from_file
from services.routes_loading.processor import load_data
from shared.config import get_settings
from shared.database import get_database
from shared.exceptions.routes_loading import PointsWithNanException
from shared.models.upoader_fields_config import UploaderFieldsConfig
from shared.resources import Resources
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/data")
settings = get_settings()


@router.post("/update-from-gsheets")
async def update_from_gsheets(
    _: Annotated[None, Depends(request_auth)],
    fields_config: Annotated[UploaderFieldsConfig, Depends(get_fields_config_from_file)],
    db_session: Annotated[AsyncSession, Depends(get_database().session)],
    gsheets_url: str = settings.DEFAULT_GSHEETS_URL,
    sea_routes_ws_name: str = settings.DEFAULT_SEA_ROUTES_WS,
    rail_routes_ws_name: str = settings.DEFAULT_RAIL_ROUTES_WS,
    truck_routes_ws_name: str = settings.DEFAULT_TRUCK_ROUTES_WS,
    dropp_routes_ws_name: str = settings.DEFAULT_DROPP_ROUTES_WS,
    points_ws_name: str | None = settings.DEFAULT_POINTS_WS,
    services_ws_name: str | None = settings.DEFAULT_SERVICES_WS,
    load_on_warnings: bool = True,
    data_file: Annotated[bytes | None, File()] = None,
):
    return await update_from_gsheets_with_custom_fields(
        db_session,
        fields_config,
        gsheets_url,
        sea_routes_ws_name,
        rail_routes_ws_name,
        truck_routes_ws_name,
        dropp_routes_ws_name,
        points_ws_name,
        services_ws_name,
        load_on_warnings,
        data_file,
    )


@router.post("/update-from-gsheets-with-custom-fields")
async def update_from_gsheets_with_custom_fields(  # noqa: C901  # TODO: split it by worksheets
    db_session: Annotated[AsyncSession, Depends(get_database().session)],
    fields_config: UploaderFieldsConfig,
    gsheets_url: str = settings.DEFAULT_GSHEETS_URL,
    sea_routes_ws_name: str = settings.DEFAULT_SEA_ROUTES_WS,
    rail_routes_ws_name: str = settings.DEFAULT_RAIL_ROUTES_WS,
    truck_routes_ws_name: str = settings.DEFAULT_TRUCK_ROUTES_WS,
    dropp_routes_ws_name: str = settings.DEFAULT_DROPP_ROUTES_WS,
    points_ws_name: str | None = settings.DEFAULT_POINTS_WS,
    services_ws_name: str | None = settings.DEFAULT_SERVICES_WS,
    load_on_warnings: bool = True,
    data_file: Annotated[bytes | None, File()] = None,
):
    if data_file:
        def download_data(ws):
            return pandas.read_excel(BytesIO(data_file), ws)
    else:
        try:
            gs = gspread.service_account(
                filename=Resources.get(settings.GOOGLE_SERVICE_ACCOUNT_RESOURCE_NAME, scope="backend_admin").path,
            )
            sources_gs = gs.open_by_url(gsheets_url)
        except Exception as e:
            raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail={
                "type": type(e).__name__,
                "detail": str(e),
            }) from e

        def download_data(ws):
            return get_as_dataframe(
                sources_gs.worksheet(ws),
                evaluate_formulas=True,
            )

    try:
        sea_routes_df = download_data(sea_routes_ws_name)
        rail_routes_df = download_data(rail_routes_ws_name)
        truck_routes_df = download_data(truck_routes_ws_name)
        dropp_routes_df = download_data(dropp_routes_ws_name)
        services_df = download_data(services_ws_name)
        points_df = download_data(points_ws_name) if points_ws_name else None

    except Exception as e:
        raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail={
            "type": type(e).__name__,
            "detail": str(e),
        }) from e

    routes_count = len(sea_routes_df) + len(rail_routes_df) + len(truck_routes_df)
    try:
        res, res_metadata, warnings = await load_data(
            db_session,
            sea_routes_df,
            rail_routes_df,
            truck_routes_df,
            dropp_routes_df,
            services_df,
            points_df,
            fields_config,
            load_on_warnings,
        )

    except PointsWithNanException as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail={
            "error": f"Ошибка в листе '{points_ws_name}': не заполнены ячейки на следующих строках:",
            "row_numbers": e.row_numbers,
        }) from e

    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail={
            "type": type(e).__name__,
            "detail": str(e),
        }) from e

    if not res:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail={
            "error": "Несколько ошибок во время загрузки данных из листов"
                     f"'{sea_routes_ws_name}' и '{rail_routes_ws_name}'"
                     ". Выполните поиск по таблице, чтобы найти ошибки",
            "errors_list": parse_all_warning_types(warnings, fields_config),
        })

    parsed_warnings = parse_all_warning_types(warnings, fields_config)

    return {
        "routesCount": str(routes_count),
        "routesInsertedCount": str(res_metadata),
        "warnings": parsed_warnings,
    }
