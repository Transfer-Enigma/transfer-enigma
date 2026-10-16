from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.errors import (
    CompanyNotFoundException,
    InvalidDroppRow,
    InvalidRouteConditionException,
    InvalidRouteTypeException,
    NoPriceInRouteException,
    PointNotFoundException,
)
from backend_admin.service.routes_loading.sync_errors import SyncError, SyncErrorCode, get_message
from module_shared.schemas.route import RouteType


def to_sync_error(data: dict) -> SyncError:
    return SyncError(**{key: value for key, value in data.items() if key in SyncError.model_fields})


def parse_all_warning_types(warnings, fc, document=None):
    seen_errors: dict[tuple, dict] = {}
    for err in warnings:
        if issubclass(type(err[0]), Exception):
            parsed = parse_error(err[0], err[1], err[2], document=document)
            dedup_key = (parsed["code"], parsed["sheet"], parsed["row"], parsed["message"])
            seen_errors.setdefault(dedup_key, parsed)

    parsed_warnings = [
        parse_warning(warning[0], warning[1], warning[2], fc, document=document)
        for warning in warnings
        if not issubclass(type(warning[0]), Exception)
    ]

    return list(seen_errors.values()) + parsed_warnings


def _structured(code: SyncErrorCode, legacy_error: str, document=None, sheet=None,
                row=None, cell=None, severity="error", **extra) -> dict:
    entry = SyncError(
        document=document,
        sheet=sheet,
        row=row,
        cell=cell,
        code=code,
        message=legacy_error,
        severity=severity,
    )
    return {
        **entry.model_dump(),
        # Deprecated, kept for backward compatibility with the admin frontend.
        "error": legacy_error,
        **extra,
    }


def parse_error(error, row_number, routes_ws_type, document=None):
    row_number += 2
    routes_ws_map = {
        RouteType.SEA: "МОРЕ",
        RouteType.RAIL: "ЖД",
        RouteType.TRUCK: "АВТО",
        None: "ДРОПП",
    }
    routes_ws = routes_ws_map.get(routes_ws_type, "Неизвестный")

    if isinstance(error, InvalidRouteConditionException):
        code = SyncErrorCode.BAD_ENUM_VALUE
        legacy = get_message(code, sheet=routes_ws, row=row_number,
                             value=error.condition, field="условия поставки")

    elif isinstance(error, PointNotFoundException):
        code = SyncErrorCode.POINT_NOT_FOUND
        legacy = get_message(code, sheet=routes_ws, row=row_number, key=error.error_key)

    elif isinstance(error, CompanyNotFoundException):
        code = SyncErrorCode.COMPANY_NOT_FOUND
        legacy = get_message(code, sheet=routes_ws, row=row_number, key=error.error_key)

    elif isinstance(error, InvalidRouteTypeException):
        code = SyncErrorCode.BAD_ENUM_VALUE
        legacy = get_message(code, sheet=routes_ws, row=row_number,
                             value=error.route_type, field="тип маршрута")

    elif isinstance(error, NoPriceInRouteException):
        code = SyncErrorCode.NO_PRICE
        legacy = get_message(code, sheet=routes_ws, row=row_number)

    elif isinstance(error, InvalidDroppRow):
        code = SyncErrorCode.DROPP_ROW_INVALID
        legacy = get_message(code, sheet=routes_ws, row=row_number)

    else:
        code = SyncErrorCode.UNKNOWN
        legacy = get_message(code, sheet=routes_ws, row=row_number,
                             type=type(error).__name__, detail=str(error))

    return _structured(code, legacy, document=document, sheet=routes_ws, row=row_number)


def parse_warning(key, value, routes_ws_name, fields_config: UploaderFieldsConfig, document=None):
    if key == "MissingRoutesDataException":
        missing_info_parsed = []
        for invalid_row in value:
            row_number = invalid_row["row_index"] + 2
            missing_info_parsed.append({
                "error": f"Ошибка в листе {routes_ws_name} на строке {row_number} в следующих ячейках:",
                "row_number": row_number,
                "columns": invalid_row["skipped_columns"],
            })

        code = SyncErrorCode.REQUIRED_CELL_EMPTY
        legacy = get_message(code, sheet=routes_ws_name, count=len(value))
        return _structured(
            code, legacy, document=document, sheet=routes_ws_name, severity="warning",
            rows_list=missing_info_parsed,
        )

    elif key == "UnsupportedDateFormat":
        code = SyncErrorCode.BAD_DATE_FORMAT
        legacy = get_message(
            code, sheet=routes_ws_name,
            col_from=fields_config.effective_from, col_to=fields_config.effective_to,
        )
        return _structured(
            code, legacy, document=document, sheet=routes_ws_name, severity="warning",
            row_numbers=[i + 2 for i in value],
        )

    code = SyncErrorCode.UNKNOWN
    return _structured(
        code, f"Неизвестная ошибка '{key}' в листе {routes_ws_name}",
        document=document, sheet=routes_ws_name, severity="warning",
        type=key, detail=str(value),
        row_numbers=[i + 2 for i in value],
    )
