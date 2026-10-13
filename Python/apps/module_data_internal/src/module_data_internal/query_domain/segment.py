from typing import Any

from module_data_internal.query_domain.expr import ColumnRef
from module_shared.schemas.route import RouteType


class Segment:
    _COLUMN_MAP: dict[str, str] = {
        "type": "type",
        "is_through": "is_through",
        "container_owner": "container_owner",
        "effective_from": "effective_from",
        "effective_to": "effective_to",
        "start_point": "start_point_id",
        "end_point": "end_point_id",
        "company": "company_id",
        "drop_off_point": "dropp_off_point_id",
    }

    def __init__(self, _type: RouteType | str | None = None) -> None:
        if isinstance(_type, str):
            _type = RouteType(_type)
        self._type_filter = _type

    def __getattr__(self, name: str) -> Any:
        col = self._COLUMN_MAP.get(name)
        if col is not None:
            return ColumnRef(self, col)
        raise AttributeError(f"'{type(self).__name__}' has no column '{name}'")

    def __repr__(self) -> str:
        parts = []
        if self._type_filter is not None:
            parts.append(f"type={self._type_filter.value}")
        return f"Segment({', '.join(parts)})" if parts else "Segment()"
