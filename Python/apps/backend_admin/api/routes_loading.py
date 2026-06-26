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
from backend_admin.config import get_settings
from backend_admin.dependencies.auth import request_auth
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.errors import (
    InvalidDropOffRow,
    InvalidRouteConditionException,
    InvalidRouteSegmentTypeException,
    NoPriceInRouteException,
    PointNotFoundException,
    PointsWithNanException,
)
from backend_admin.service.routes_loading.processor import load_data
from gspread_dataframe import get_as_dataframe
from module_data_internal.schemas import RouteSegmentType
from module_shared.database import get_database
from module_shared.resources import Resources
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/data")
settings = get_settings()


def get_fields_config_from_file():
    return UploaderFieldsConfig(
        **Resources.get(settings.DEFAULT_UPLOADER_FIELDS_CONFIG_RESOURCE_NAME, scope="backend_admin").read_json(),
    )


@router.post("/update-from-gsheets")
async def update_from_gsheets(
    _: Annotated[None, Depends(request_auth)],
    fields_config: Annotated[UploaderFieldsConfig, Depends(get_fields_config_from_file)],
    db_session: Annotated[AsyncSession, Depends(get_database().session)],
    gsheets_url: str = settings.DEFAULT_GSHEETS_URL,
    sea_routes_ws_name: str = settings.DEFAULT_SEA_ROUTES_WS,
    rail_routes_ws_name: str = settings.DEFAULT_RAIL_ROUTES_WS,
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
        dropp_routes_df = download_data(dropp_routes_ws_name)
        services_df = download_data(services_ws_name)
        points_df = download_data(points_ws_name) if points_ws_name else None

    except Exception as e:
        raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail={
            "type": type(e).__name__,
            "detail": str(e),
        }) from e

    routes_count = len(sea_routes_df) + len(rail_routes_df)
    try:
        res, res_metadata, warnings = await load_data(
            db_session,
            sea_routes_df,
            rail_routes_df,
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


def parse_all_warning_types(warnings, fc):
    return list({
        parse_error(err[0], err[1], err[2])
        for err in warnings
        if issubclass(type(err[0]), Exception)
    }) + [
        parse_warning(warning[0], warning[1], warning[2], fc)
        for warning in warnings
        if not issubclass(type(warning[0]), Exception)
    ]


def parse_error(error, row_number, routes_ws_type):
    row_number += 2
    routes_ws = {RouteSegmentType.SEA: "МОРЕ", RouteSegmentType.RAIL: "ЖД", None: "ДРОП-ОФФ"}.get(routes_ws_type, "Неизвестный")

    if isinstance(error, InvalidRouteConditionException):
        return f"Неверные условия поставки: '{error.condition}' (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, PointNotFoundException):
        return f"Не найден город или порт: '{error.error_key}' (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, InvalidRouteSegmentTypeException):
        return f"Неверный тип маршрута: '{error.route_type}' (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, NoPriceInRouteException):
        return f"Отсутствуют цены в маршруте (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, InvalidDropOffRow):
        return f"Неверный формат данных в листе {routes_ws} на строке {row_number}"

    return f"Неизвестная ошибка {type(error).__name__}: '{error}' (лист {routes_ws}, строка {row_number})"


def parse_warning(key, value, routes_ws_name, fields_config: UploaderFieldsConfig):
    if key == "MissingRoutesDataException":
        missing_info_parsed = []
        for invalid_row in value:
            row_number = invalid_row["row_index"] + 2
            missing_info_parsed.append({
                "error": f"Ошибка в листе {routes_ws_name} на строке {row_number} в следующих ячейках:",
                "row_number": row_number,
                "columns": invalid_row["skipped_columns"],
            })

        return {
            "error": f"Ошибка в листе {routes_ws_name}: не заполнены обязательные столбцы "
                     f"в следующих строках ({len(value)}):",
            "rows_list": missing_info_parsed,
        }

    elif key == "UnsupportedDateFormat":
        return {
            "error": f"Ошибка в листе {routes_ws_name}: неподдерживаемый формат столбцов "
                     f"{fields_config.effective_from}/{fields_config.effective_to}:",
            "row_numbers": [i + 2 for i in value],
        }

    return {
        "error": f"Неизвестная ошибка '{key}' в листе {routes_ws_name}",
        "row_numbers": [i + 2 for i in value],
    }
