from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, File
from starlette.status import HTTP_400_BAD_REQUEST

import gspread
import pandas
from backend_admin.config import get_settings
from backend_admin.dependencies.auth import request_auth
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.error_reporting import parse_all_warning_types
from backend_admin.service.routes_loading.errors import PointsWithNanException
from backend_admin.service.routes_loading.processor import load_data
from backend_admin.service.routes_loading.sync_errors import (
    gsheets_unavailable_error,
    points_sheet_nan_error,
    unexpected_error,
    ws_not_found_error,
)
from backend_admin.service.routes_loading.validation import load_reference_snapshot, validate_frames
from gspread_dataframe import get_as_dataframe
from module_shared.database import get_database
from module_shared.resources import Resources
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/data")
settings = get_settings()


def get_fields_config_from_file():
    return UploaderFieldsConfig(
        **Resources.get(settings.DEFAULT_UPLOADER_FIELDS_CONFIG_RESOURCE_NAME, scope="backend_admin").read_json(),
    )


def _download_all(data_file, gsheets_url, sea_routes_ws_name, rail_routes_ws_name,
                  truck_routes_ws_name, dropp_routes_ws_name,
                  services_ws_name, points_ws_name) -> tuple[dict, str | None]:
    if data_file:
        def download_data(ws):
            return pandas.read_excel(BytesIO(data_file), ws)

        document = None
    else:
        try:
            gs = gspread.service_account(
                filename=Resources.get(settings.GOOGLE_SERVICE_ACCOUNT_RESOURCE_NAME, scope="backend_admin").path,
            )
            sources_gs = gs.open_by_url(gsheets_url)
        except Exception as e:
            raise gsheets_unavailable_error(e, document=gsheets_url) from e

        def download_data(ws):
            return get_as_dataframe(
                sources_gs.worksheet(ws),
                evaluate_formulas=True,
            )

        document = gsheets_url

    try:
        frames = {
            "sea": download_data(sea_routes_ws_name),
            "rail": download_data(rail_routes_ws_name),
            "truck": download_data(truck_routes_ws_name),
            "dropp": download_data(dropp_routes_ws_name),
            "services": download_data(services_ws_name),
            "points": download_data(points_ws_name) if points_ws_name else None,
        }
    except Exception as e:
        raise ws_not_found_error(e, document=document) from e

    return frames, document


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
async def update_from_gsheets_with_custom_fields(  # TODO: split it by worksheets
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
    frames, document = _download_all(
        data_file,
        gsheets_url,
        sea_routes_ws_name,
        rail_routes_ws_name,
        truck_routes_ws_name,
        dropp_routes_ws_name,
        services_ws_name,
        points_ws_name,
    )

    routes_count = len(frames["sea"]) + len(frames["rail"]) + len(frames["truck"])
    try:
        res, res_metadata, warnings = await load_data(
            db_session,
            frames["sea"],
            frames["rail"],
            frames["truck"],
            frames["dropp"],
            frames["services"],
            frames["points"],
            fields_config,
            load_on_warnings,
        )

    except PointsWithNanException as e:
        raise points_sheet_nan_error(e.row_numbers, sheet=points_ws_name) from e

    except Exception as e:
        raise unexpected_error(e, document=document) from e

    if not res:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail={
            "error": "Несколько ошибок во время загрузки данных из листов"
                     f"'{sea_routes_ws_name}' и '{rail_routes_ws_name}'"
                     ". Выполните поиск по таблице, чтобы найти ошибки",
            "errors_list": parse_all_warning_types(warnings, fields_config, document=document),
        })

    parsed_warnings = parse_all_warning_types(warnings, fields_config, document=document)

    return {
        "routesCount": str(routes_count),
        "routesInsertedCount": str(res_metadata),
        "warnings": parsed_warnings,
    }


@router.post("/validate-from-gsheets")
async def validate_from_gsheets(
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
    data_file: Annotated[bytes | None, File()] = None,
):
    frames, document = _download_all(
        data_file,
        gsheets_url,
        sea_routes_ws_name,
        rail_routes_ws_name,
        truck_routes_ws_name,
        dropp_routes_ws_name,
        services_ws_name,
        points_ws_name,
    )
    snapshot = await load_reference_snapshot(db_session)
    report = validate_frames(
        frames["sea"],
        frames["rail"],
        frames["truck"],
        frames["dropp"],
        frames["services"],
        frames["points"],
        fields_config,
        snapshot,
        document=document,
        points_sheet=points_ws_name or "points",
    )
    return report.to_dict()
