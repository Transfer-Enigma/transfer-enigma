import re

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.helpers import format_date
from pandas import DataFrame

FIXABLE_FRAMES = ("sea", "rail", "truck", "dropp", "points")


def _collapse_spaces(value: str) -> str:
    return re.sub(r" {2,}", " ", value.strip())


def _fix_string_cell(value, upper: bool = False):
    if not isinstance(value, str):
        return value, False
    fixed = _collapse_spaces(value)
    if upper:
        fixed = fixed.upper()
    return fixed, fixed != value


def _fix_date_cell(value):
    if not isinstance(value, str) or not value.strip():
        return value, False
    fixed = format_date(value)
    if not fixed or fixed == value:
        return value, False
    return fixed, True


def apply_fixes(frames: dict[str, DataFrame | None], fc: UploaderFieldsConfig) -> tuple[dict, list[dict]]:
    fixed_frames = {}
    fixes = []
    for key, frame in frames.items():
        if frame is None or key not in FIXABLE_FRAMES:
            fixed_frames[key] = frame
            continue
        fixed_frames[key], frame_fixes = _fix_frame(key, frame.copy(), fc)
        fixes.extend(frame_fixes)
    return fixed_frames, fixes


def _fix_frame(key: str, frame: DataFrame, fc: UploaderFieldsConfig) -> tuple[DataFrame, list[dict]]:
    fixes = []
    upper_columns = {fc.company, fc.terminal} if key != "points" else set()
    date_columns = {fc.effective_from, fc.effective_to} if key != "points" else set()

    for column in frame.columns:
        if column in date_columns:
            for idx, value in frame[column].items():
                if pd.isna(value):
                    continue
                fixed, changed = _fix_date_cell(value)
                if changed:
                    frame.at[idx, column] = fixed
                    fixes.append(_fix_entry(key, idx, column, value, fixed))
            continue
        upper = column in upper_columns
        for idx, value in frame[column].items():
            if pd.isna(value) or not isinstance(value, str):
                continue
            fixed, changed = _fix_string_cell(value, upper)
            if changed:
                frame.at[idx, column] = fixed
                fixes.append(_fix_entry(key, idx, column, value, fixed))
    return frame, fixes


def _fix_entry(key: str, idx, column: str, old, new) -> dict:
    return {
        "sheet": key,
        "row": idx + 2,
        "column": column,
        "old": old,
        "new": new,
    }
