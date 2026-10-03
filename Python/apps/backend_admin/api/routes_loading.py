from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Response
from fastapi.params import Depends, File, Query
from starlette.status import HTTP_400_BAD_REQUEST

import gspread
from backend_admin.config import get_settings
from backend_admin.dependencies.auth import request_auth
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading import documents as document_service
from backend_admin.service.routes_loading.artifacts import build_report_workbook
from backend_admin.service.routes_loading.fixes import apply_fixes
from backend_admin.service.routes_loading.inputs import (
    bad_input_error,
    read_upload,
    select_upload_frames,
)
from backend_admin.service.routes_loading.loading import synchronize
from backend_admin.service.routes_loading.report import build_affected_rows
from backend_admin.service.routes_loading.sync_errors import (
    SyncErrorCode,
    gsheets_unavailable_error,
    points_sheet_nan_error,
    unexpected_error,
    ws_not_found_error,
)
from backend_admin.service.routes_loading.uid_sheet import (
    ensure_sheet_uids,
    highlight_report_cells,
    write_fix_cells,
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
                  services_ws_name, points_ws_name,
                  only_sheets: set[str] | None = None) -> tuple[dict, str | None, dict]:
    worksheets: dict[str, object] = {}
    if data_file:
        parsed = read_upload(data_file)
        requested_names = {
            "sea": sea_routes_ws_name,
            "rail": rail_routes_ws_name,
            "truck": truck_routes_ws_name,
            "dropp": dropp_routes_ws_name,
            "services": services_ws_name,
            "points": points_ws_name,
        }
        if only_sheets is not None:
            requested_names = {
                key: (ws_name if key in only_sheets else None)
                for key, ws_name in requested_names.items()
            }
        frames = select_upload_frames(parsed, requested_names)
        return frames, None, worksheets

    try:
        gs = gspread.service_account(
            filename=Resources.get(settings.GOOGLE_SERVICE_ACCOUNT_RESOURCE_NAME, scope="backend_admin").path,
        )
        sources_gs = gs.open_by_url(gsheets_url)
    except Exception as e:
        raise gsheets_unavailable_error(e, document=gsheets_url) from e

    def download_data(ws):
        worksheets[ws] = sources_gs.worksheet(ws)
        return get_as_dataframe(
            worksheets[ws],
            evaluate_formulas=True,
        )

    document = gsheets_url

    try:
        requested = {
            "sea": sea_routes_ws_name,
            "rail": rail_routes_ws_name,
            "truck": truck_routes_ws_name,
            "dropp": dropp_routes_ws_name,
            "services": services_ws_name,
            "points": points_ws_name,
        }
        frames = {}
        for key, ws_name in requested.items():
            if not ws_name or (only_sheets is not None and key not in only_sheets):
                frames[key] = None
            else:
                frames[key] = download_data(ws_name)
    except Exception as e:
        raise ws_not_found_error(e, document=document) from e

    return frames, document, worksheets


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
    document_id: int | None = None,
    mode: Literal["all", "new"] = "all",
    fix: bool = False,
    sheets: Annotated[list[str] | None, Query()] = None,
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
        document_id,
        mode,
        fix,
        sheets,
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
    document_id: int | None = None,
    mode: Literal["all", "new"] = "all",
    fix: bool = False,
    sheets: Annotated[list[str] | None, Query()] = None,
):
    sync_document = None
    if document_id is not None:
        sync_document = await document_service.resolve_document(db_session, document_id)
        gsheets_url = sync_document.url
        sea_routes_ws_name = sync_document.sea_ws
        rail_routes_ws_name = sync_document.rail_ws
        truck_routes_ws_name = sync_document.truck_ws
        dropp_routes_ws_name = sync_document.dropp_ws
        points_ws_name = sync_document.points_ws
        services_ws_name = sync_document.services_ws

    frames, document, worksheets = _download_all(
        data_file,
        gsheets_url,
        sea_routes_ws_name,
        rail_routes_ws_name,
        truck_routes_ws_name,
        dropp_routes_ws_name,
        services_ws_name,
        points_ws_name,
        only_sheets=set(sheets) if sheets else None,
    )

    fixes: list[dict] = []
    if fix:
        frames, fixes = apply_fixes(frames, fields_config)
        if worksheets:
            write_fix_cells(
                worksheets,
                {
                    "sea": ("SEA", sea_routes_ws_name),
                    "rail": ("RAIL", rail_routes_ws_name),
                    "truck": ("TRUCK", truck_routes_ws_name),
                    "dropp": ("DROPP", dropp_routes_ws_name),
                },
                fixes,
            )

    routes_count = sum(len(frames[key]) for key in ("sea", "rail", "truck") if frames[key] is not None)
    try:
        outcome = await synchronize(
            db_session,
            frames,
            fields_config,
            document,
            load_on_warnings,
            update_existing=(mode == "all"),
            sync_document_id=sync_document.id if sync_document else None,
            uid_column=sync_document.uid_column if sync_document else "__uid",
        )
    except Exception as e:
        raise unexpected_error(e, document=document) from e

    if sync_document is not None:
        document_service.record_sync_status(
            sync_document,
            outcome.ok,
            len(outcome.report.errors) + len(outcome.report.warnings),
        )

    if not outcome.ok:
        errors = outcome.report.errors
        warnings = outcome.report.warnings
        points_fatal = [error for error in errors if error.code == SyncErrorCode.POINTS_SHEET_NAN]
        if len(errors) == 1 and not warnings and points_fatal and points_fatal[0].details:
            raise points_sheet_nan_error(
                points_fatal[0].details.get("row_numbers", []), sheet=points_ws_name,
            )
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail={
            "error": "Несколько ошибок во время загрузки данных из листов"
                     f"'{sea_routes_ws_name}' и '{rail_routes_ws_name}'"
                     ". Выполните поиск по таблице, чтобы найти ошибки",
            "errors_list": [error.model_dump() for error in (*errors, *warnings)],
        })

    return {
        "routesCount": str(routes_count),
        "routesInsertedCount": str(outcome.built_routes),
        "deletedRoutesCount": str(outcome.deleted_routes),
        "deletedDroppCount": str(outcome.deleted_dropp),
        "warnings": [finding.model_dump() for finding in (*outcome.report.errors, *outcome.report.warnings)],
        "fixes": fixes,
        "affected_rows": build_affected_rows(outcome.validated, fixes, fields_config)
        if outcome.validated
        else [],
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
    document_id: int | None = None,
    ensure_uids: bool = False,
    fix: bool = False,
    highlight: bool = False,
    artifact: Literal["report", "file"] = "report",
    sheets: Annotated[list[str] | None, Query()] = None,
):
    sync_document = None
    if document_id is not None:
        sync_document = await document_service.resolve_document(db_session, document_id)
        gsheets_url = sync_document.url
        sea_routes_ws_name = sync_document.sea_ws
        rail_routes_ws_name = sync_document.rail_ws
        truck_routes_ws_name = sync_document.truck_ws
        dropp_routes_ws_name = sync_document.dropp_ws
        points_ws_name = sync_document.points_ws
        services_ws_name = sync_document.services_ws

    uid_column = sync_document.uid_column if sync_document else "__uid"
    frames, document, worksheets = _download_all(
        data_file,
        gsheets_url,
        sea_routes_ws_name,
        rail_routes_ws_name,
        truck_routes_ws_name,
        dropp_routes_ws_name,
        services_ws_name,
        points_ws_name,
        only_sheets=set(sheets) if sheets else None,
    )
    fixes: list[dict] = []
    if fix:
        frames, fixes = apply_fixes(frames, fields_config)
        if worksheets:
            write_fix_cells(
                worksheets,
                {
                    "sea": ("SEA", sea_routes_ws_name),
                    "rail": ("RAIL", rail_routes_ws_name),
                    "truck": ("TRUCK", truck_routes_ws_name),
                    "dropp": ("DROPP", dropp_routes_ws_name),
                },
                fixes,
            )
    snapshot = await load_reference_snapshot(db_session)
    validated = validate_frames(
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
        uid_column=uid_column,
    )
    uids_written = 0
    if ensure_uids and worksheets:
        uids_written = ensure_sheet_uids(
            worksheets,
            {
                "sea": ("SEA", sea_routes_ws_name),
                "rail": ("RAIL", rail_routes_ws_name),
                "truck": ("TRUCK", truck_routes_ws_name),
                "dropp": ("DROPP", dropp_routes_ws_name),
            },
            validated.row_uids,
            uid_column,
        )
    if sync_document is not None:
        document_service.record_validation_status(
            sync_document,
            len(validated.report.errors) + len(validated.report.warnings),
        )
    findings = [*validated.report.errors, *validated.report.warnings]
    highlighted = 0
    if highlight and worksheets:
        highlighted = highlight_report_cells(
            worksheets,
            {
                "sea": ("SEA", sea_routes_ws_name),
                "rail": ("RAIL", rail_routes_ws_name),
                "truck": ("TRUCK", truck_routes_ws_name),
                "dropp": ("DROPP", dropp_routes_ws_name),
            },
            findings,
        )
    if artifact == "file":
        if not data_file:
            raise bad_input_error("artifact=file requires an uploaded file")
        content = build_report_workbook(
            frames,
            findings,
            fixes,
            {
                "sea": sea_routes_ws_name,
                "rail": rail_routes_ws_name,
                "truck": truck_routes_ws_name,
                "dropp": dropp_routes_ws_name,
                "services": services_ws_name,
                "points": points_ws_name,
            },
        )
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="validated.xlsx"'},
        )
    return {
        **validated.report.to_dict(),
        "uids_written": uids_written,
        "fixes": fixes,
        "highlighted": highlighted,
        "affected_rows": build_affected_rows(validated, fixes, fields_config),
    }
