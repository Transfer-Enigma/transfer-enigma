from typing import Any

from module_data_internal.query_domain.expr import ColumnRef, Condition


class DropOff:
    _COLUMN_MAP: dict[str, str] = {
        "id": "id",
        "company": "company_id",
        "container": "container_id",
        "start_point": "start_point_id",
        "end_point": "end_point_id",
        "effective_from": "effective_from",
        "effective_to": "effective_to",
    }

    def __getattr__(self, name: str) -> Any:
        col = self._COLUMN_MAP.get(name)
        if col is not None:
            return ColumnRef(self, col)
        raise AttributeError(f"'{type(self).__name__}' has no column '{name}'")

    def exists(self) -> Condition:
        return self.id.not_null()

    def __repr__(self) -> str:
        return "DropOff()"
