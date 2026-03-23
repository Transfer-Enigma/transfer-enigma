import json

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

import gspread
from back_admin.config import get_settings
from back_admin.service.routes_loading.errors import (
    InvalidRouteConditionCurrencyPairException,
    InvalidRouteConditionException,
    InvalidRouteConditionPricesException,
    InvalidRouteTypeException,
    LoadingErrorException,
    PointNotFoundException,
    PointsWithNanException,
)
from back_admin.service.routes_loading.processor import load_data
from gspread_dataframe import get_as_dataframe
from shared.database import get_database
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/data")
settings = get_settings()


def get_fields_config_from_file(path: str = settings.DEFAULT_UPLOADER_FIELDS_CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data


@router.post("/update-from-gsheets")
async def update_from_gsheets(
    gsheets_url: str = settings.GSHEETS_URL,
    routes_ws_name: str = settings.ROUTES_WS,
    points_ws_name: str | None = settings.POINTS_WS,
    load_on_warnings: bool = True,
    fields_config: dict[str, str] = Depends(get_fields_config_from_file),
    db_session: AsyncSession = Depends(get_database().session),
):
    return await update_from_gsheets_with_custom_fields(
        fields_config,
        gsheets_url,
        routes_ws_name,
        points_ws_name,
        load_on_warnings,
        db_session,
    )


@router.post("/update-from-gsheets-with-custom-fields")
async def update_from_gsheets_with_custom_fields(
    fields_config: dict[str, str],
    gsheets_url: str = settings.GSHEETS_URL,
    routes_ws_name: str = settings.ROUTES_WS,
    points_ws_name: str | None = settings.POINTS_WS,
    load_on_warnings: bool = True,
    db_session: AsyncSession = Depends(get_database().session),
):
    gs = gspread.service_account(filename=settings.GOOGLE_SERVICE_ACCOUNT_FILE_PATH)
    sources_gs = gs.open_by_url(gsheets_url)

    routes_df = get_as_dataframe(
        sources_gs.worksheet(routes_ws_name),
        evaluate_formulas=True,
    )
    points_df = get_as_dataframe(
        sources_gs.worksheet(points_ws_name),
        evaluate_formulas=True,
    ) if points_ws_name else None

    routes_count = len(routes_df)
    try:
        res, res_metadata, warnings = await load_data(
            db_session,
            routes_df,
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
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=e) from e

    if not res:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail={
            "error": f"Несколько ошибок во время загрузки данных из листа '{routes_ws_name}'. "
                     "Сделайте поиск по таблице, чтобы найти ошибки",
            "errors_list": parse_all_warning_types(warnings, routes_ws_name, fields_config),
        })

    parsed_warnings = parse_all_warning_types(warnings, routes_ws_name, fields_config)

    return {
        "routesCount": str(routes_count),
        "routesInsertedCount": str(res_metadata),
        "warnings": parsed_warnings,
    }


def parse_all_warning_types(warnings, routes_ws_name, fc):
    return list({
        parse_error(err)
        for err in warnings
        if isinstance(err, LoadingErrorException)
    }) + [
        parse_warning(warning[0], warning[1], routes_ws_name, fc)
        for warning in warnings
        if not isinstance(warning, LoadingErrorException)
    ]


def parse_error(error):
    if isinstance(error, InvalidRouteTypeException):
        return f"Неверный тип маршрута: '{error.route_type}'"

    elif isinstance(error, InvalidRouteConditionException):
        return f"Неверные условия поставки: '{error.condition}'"

    elif isinstance(error, InvalidRouteConditionCurrencyPairException):
        return (
            "Нерерная конфигурация ячеек 'условия поставки', 'валюта', 'тип маршрута': "
            f"'{error.conditions}', '{error.currencies}', '{error.route_type}'"
        )

    elif isinstance(error, PointNotFoundException):
        return f"Не найден город или порт: '{error.error_key}'"

    elif isinstance(error, InvalidRouteConditionPricesException):
        return (
            f"Неверная конфигурация ячеек цены на ЖД/МОРЕ при условиях поставки {error.condition}: "
            "МОРЕ - " + (", ".join(error.sea_prices)) + "; "
            "ЖД - " + (", ".join(error.rail_prices))
        )


def parse_warning(key, value, routes_ws_name, fields_config):
    if key == "MissingRoutesDataException":
        missing_info_parsed = []
        for invalid_row in value:
            row_number = invalid_row["row_index"] + 2
            missing_info_parsed.append({
                "error": f"Ошибка в строке {row_number} в следующих ячейках:",
                "row_number": row_number,
                "columns": invalid_row["skipped_columns"],
            })

        return {
            "error": f"Ошибка в листе '{routes_ws_name}': не заполнены обязательные столбцы "
                     f"в следующих строках ({len(value)}):",
            "rows_list": missing_info_parsed,
        }

    elif key == "UnsupportedDateFormat":
        return {
            "error": f"Ошибка в листе '{routes_ws_name}': неподдерживаемый формат столбцов "
                     f"{fields_config['effective_from']}/{fields_config['effective_to']}:",
            "row_numbers": [i + 2 for i in value],
        }
