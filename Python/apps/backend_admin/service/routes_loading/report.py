from contextlib import suppress

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.validation import SHEET_LABELS, ValidatedData
from module_shared.schemas.route import RouteType
from pandas import DataFrame

SCOPE_SHEETS = {
    "SEA": RouteType.SEA,
    "RAIL": RouteType.RAIL,
    "TRUCK": RouteType.TRUCK,
}


def _jsonable(value):
    with suppress(TypeError, ValueError):
        if pd.isna(value):
            return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "item"):
        with suppress(TypeError, ValueError):
            return value.item()
    return value


def _row_frame(validated: ValidatedData, fc: UploaderFieldsConfig, scope: str) -> DataFrame | None:
    if scope == "DROPP":
        return validated.dropp_df
    route_type = SCOPE_SHEETS.get(scope)
    if route_type is None:
        return None
    frame = validated.routes_df
    if fc.route_type not in frame.columns:
        return None
    return frame[frame[fc.route_type] == route_type]


def _frame_row(frame: DataFrame, orig_idx: int) -> dict:
    try:
        row = frame.loc[orig_idx]
    except KeyError:
        return {}
    if hasattr(row, "iloc") and getattr(row, "ndim", 1) > 1:
        row = row.iloc[0]
    return {str(column): _jsonable(row[column]) for column in frame.columns}


def build_affected_rows(validated: ValidatedData, fixes: list[dict],
                        fc: UploaderFieldsConfig) -> list[dict]:
    fixes_by_row: dict[tuple[str, int], list[dict]] = {}
    for fix in fixes:
        scope = {"sea": "SEA", "rail": "RAIL", "truck": "TRUCK", "dropp": "DROPP"}.get(fix.get("sheet", ""))
        if scope and fix.get("row"):
            fixes_by_row.setdefault((scope, fix["row"] - 2), []).append(fix)

    affected = []
    for (scope, orig_idx), uid in validated.row_uids.items():
        row_number = orig_idx + 2
        errors = validated.row_errors.get((scope, orig_idx), [])
        row_fixes = fixes_by_row.get((scope, orig_idx), [])
        if not errors and not row_fixes:
            continue
        frame = _row_frame(validated, fc, scope)
        values = _frame_row(frame, orig_idx) if frame is not None else {}
        affected.append({
            "document": validated.document,
            "scope": scope,
            "sheet": _sheet_label(scope),
            "row": row_number,
            "uid": uid,
            "values": values,
            "fixed": bool(row_fixes),
            "errors": [error.model_dump() for error in errors],
            "fixes": row_fixes,
        })
    affected.sort(key=lambda entry: (entry["scope"], entry["row"]))
    return affected


def _sheet_label(scope: str) -> str:
    for route_type, label in SHEET_LABELS.items():
        if route_type is not None and route_type.value == scope:
            return label
    if scope == "DROPP":
        return SHEET_LABELS[None]
    return scope
