import datetime
from typing import Any

from backend_admin.schemas.data_browser import DropOffCreate, DropOffPatch, DropOffResponse
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_data_internal.schemas import DropModel


def _parse_date(value: str) -> datetime.date:
    return datetime.date.fromisoformat(value)


class CRUDDropOff(CRUDBase):
    model = DropModel
    create_schema = DropOffCreate
    update_schema = DropOffCreate
    patch_schema = DropOffPatch
    response_schema = DropOffResponse
    list_filters = [
        FilterDef("company_id", "company_id", "eq"),
        FilterDef("container_id", "container_id", "eq"),
    ]

    def _build_instance(self, data: DropOffCreate) -> DropModel:
        return DropModel(
            container_id=data.container_id,
            company_id=data.company_id,
            start_point_id=data.start_point_id,
            end_point_id=data.end_point_id,
            effective_from=_parse_date(data.effective_from),
            effective_to=_parse_date(data.effective_to),
            price=data.price,
            conversation_percents=data.conversation_percents,
            currency=data.currency,
        )

    def _apply_update(self, model: DropModel, data: DropOffCreate) -> None:
        model.container_id = data.container_id
        model.company_id = data.company_id
        model.start_point_id = data.start_point_id
        model.end_point_id = data.end_point_id
        model.effective_from = _parse_date(data.effective_from)
        model.effective_to = _parse_date(data.effective_to)
        model.price = data.price
        model.conversation_percents = data.conversation_percents
        model.currency = data.currency

    def _apply_patch(self, model: DropModel, data: DropOffPatch) -> None:
        data_dump = data.model_dump(exclude_unset=True)
        for key, value in data_dump.items():
            if value is not None:
                converted = self._convert_patch_field(key, value)
                setattr(model, key, converted)

    def _convert_patch_field(self, key: str, value: Any) -> Any:
        converters = {
            "effective_from": _parse_date,
            "effective_to": _parse_date,
        }
        converter = converters.get(key)
        return converter(value) if converter else value


crud_drop_off = CRUDDropOff()
