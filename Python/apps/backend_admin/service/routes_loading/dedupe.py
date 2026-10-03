from contextlib import suppress

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from module_shared.schemas.route import RouteType

from .uid import payload_uid_for_dropp_values, payload_uid_for_route_values


def _cell(row, column):
    if column not in row.index:
        return None
    value = row[column]
    if value is None:
        return None
    with suppress(TypeError, ValueError):
        if pd.isna(value):
            return None
    return value


def _price_cells(row, columns: list[str]) -> dict:
    return {column: _cell(row, column) for column in columns if column in row.index}


def row_payload_uid(row, fc: UploaderFieldsConfig, route_type: RouteType | None) -> str:
    values = {
        "type": route_type.value if route_type is not None else None,
        "company": _cell(row, fc.company),
        "start_point": _cell(row, fc.start_point),
        "end_point": _cell(row, fc.end_point),
        "dropp_off_point": _cell(row, fc.dropp_off_point),
        "effective_from": _cell(row, fc.effective_from),
        "effective_to": _cell(row, fc.effective_to),
        "container_shipment_terms": _cell(row, fc.container_shipment_terms),
        "container_transfer_terms": _cell(row, fc.container_transfer_terms),
        "container_owner": _cell(row, fc.container_condition),
        "is_through": _cell(row, fc.is_through),
    }
    if route_type is None:
        return payload_uid_for_dropp_values(values, _price_cells(row, [fc.drop20, fc.drop40]))
    if route_type is RouteType.SEA:
        prices = _price_cells(row, [fc.sea_20dc, fc.sea_40hc])
    elif route_type is RouteType.RAIL:
        prices = _price_cells(row, [fc.rail_20dc24t, fc.rail_20dc28t, fc.rail_40hc])
    elif route_type is RouteType.TRUCK:
        prices = _price_cells(row, [fc.truck_20dc, fc.truck_40hc])
    else:
        prices = {}
    return payload_uid_for_route_values(values, prices)


def find_duplicate_groups(keys_uids: list) -> dict[str, list]:
    by_uid: dict[str, list] = {}
    for key, uid in keys_uids:
        by_uid.setdefault(uid, []).append(key)
    return {uid: keys for uid, keys in by_uid.items() if len(keys) > 1}
