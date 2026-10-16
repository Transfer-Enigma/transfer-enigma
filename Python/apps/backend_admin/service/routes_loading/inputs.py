from io import BytesIO

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

import pandas as pd
from pandas import DataFrame

from .documents import suggest_mapping
from .sync_errors import SyncErrorCode, make_error

SHEET_KEYS = ("sea", "rail", "truck", "dropp", "services", "points")


def read_upload(data: bytes) -> dict[str, DataFrame] | DataFrame:
    try:
        tables = pd.read_excel(BytesIO(data), sheet_name=None)
    except Exception as excel_error:
        try:
            return pd.read_csv(BytesIO(data))
        except Exception as csv_error:
            raise bad_input_error(f"excel: {excel_error}; csv: {csv_error}") from csv_error
    if not tables:
        raise bad_input_error("workbook has no worksheets")
    return tables


def bad_input_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail={
            **make_error(SyncErrorCode.BAD_INPUT_FORMAT, detail=detail).model_dump(),
            "detail": detail,
        },
    )


def select_upload_frames(parsed: dict[str, DataFrame] | DataFrame,
                         requested: dict[str, str | None]) -> dict[str, DataFrame | None]:
    if isinstance(parsed, dict):
        frames: dict[str, DataFrame | None] = {}
        for key in SHEET_KEYS:
            ws_name = requested.get(key)
            if not ws_name:
                frames[key] = None
                continue
            if ws_name not in parsed:
                raise bad_input_error(f"worksheet '{ws_name}' not found in uploaded file")
            frames[key] = parsed[ws_name]
        return frames

    selected: dict[str, DataFrame | None] = dict.fromkeys(SHEET_KEYS)
    for key in SHEET_KEYS:
        if requested.get(key):
            selected[key] = parsed
            break
    return selected


def preview_upload(data: bytes) -> dict:
    parsed = read_upload(data)
    if isinstance(parsed, dict):
        titles = list(parsed)
        single_sheet = False
    else:
        titles = ["sheet"]
        single_sheet = True
    return {
        "sheets": titles,
        "suggested_mapping": suggest_mapping(titles),
        "single_sheet": single_sheet,
    }
