import enum
import json
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from pydantic import BaseModel

Severity = Literal["error", "warning"]


class SyncErrorCode(enum.StrEnum):
    GSHEETS_UNAVAILABLE = "GSHEETS_UNAVAILABLE"
    WS_NOT_FOUND = "WS_NOT_FOUND"
    REQUIRED_CELL_EMPTY = "REQUIRED_CELL_EMPTY"
    BAD_ENUM_VALUE = "BAD_ENUM_VALUE"
    POINT_NOT_FOUND = "POINT_NOT_FOUND"
    COMPANY_NOT_FOUND = "COMPANY_NOT_FOUND"
    NO_PRICE = "NO_PRICE"
    BAD_DATE_FORMAT = "BAD_DATE_FORMAT"
    BAD_NUMBER_FORMAT = "BAD_NUMBER_FORMAT"
    POINTS_SHEET_NAN = "POINTS_SHEET_NAN"
    DROPP_ROW_INVALID = "DROPP_ROW_INVALID"
    DUPLICATE_ROW = "DUPLICATE_ROW"
    UID_NOT_IN_DB = "UID_NOT_IN_DB"
    UNKNOWN = "UNKNOWN"


class SyncError(BaseModel):
    document: str | None = None
    sheet: str | None = None
    row: int | None = None
    cell: str | None = None
    code: SyncErrorCode
    message: str
    severity: Severity = "error"
    details: dict[str, Any] | None = None


def _locales_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "locales"


def load_locale(lang: str = "ru") -> dict[str, str]:
    path = _locales_dir() / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_message(code: SyncErrorCode | str, lang: str = "ru", **params: Any) -> str:
    templates = load_locale(lang)
    key = code.value if isinstance(code, enum.Enum) else str(code)
    if key not in templates:
        raise KeyError(f"No '{lang}' template for sync error code '{key}'")
    return templates[key].format(**params)


def make_error(
    code: SyncErrorCode,
    lang: str = "ru",
    document: str | None = None,
    sheet: str | None = None,
    row: int | None = None,
    cell: str | None = None,
    severity: Severity = "error",
    **params: Any,
) -> SyncError:
    return SyncError(
        document=document,
        sheet=sheet,
        row=row,
        cell=cell,
        code=code,
        message=get_message(code, lang, sheet=sheet, row=row, **params),
        severity=severity,
    )


def gsheets_unavailable_error(exc: Exception, document: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            **make_error(
                SyncErrorCode.GSHEETS_UNAVAILABLE,
                document=document,
                detail=f"{type(exc).__name__}: {exc}",
            ).model_dump(),
            "type": type(exc).__name__,
            "detail": str(exc),
        },
    )


def ws_not_found_error(exc: Exception, sheet: str | None = None, document: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            **make_error(
                SyncErrorCode.WS_NOT_FOUND,
                document=document,
                sheet=sheet,
                detail=str(exc),
            ).model_dump(),
            "type": type(exc).__name__,
            "detail": str(exc),
        },
    )


def unexpected_error(exc: Exception, document: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            **make_error(
                SyncErrorCode.UNKNOWN,
                document=document,
                type=type(exc).__name__,
                detail=str(exc),
            ).model_dump(),
            "type": type(exc).__name__,
            "detail": str(exc),
        },
    )


def points_sheet_nan_error(row_numbers: list[int], sheet: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail={
            **make_error(
                SyncErrorCode.POINTS_SHEET_NAN,
                sheet=sheet,
            ).model_dump(),
            # Deprecated, kept for backward compatibility with the admin frontend.
            "error": get_message(SyncErrorCode.POINTS_SHEET_NAN, sheet=sheet),
            "row_numbers": row_numbers,
        },
    )
