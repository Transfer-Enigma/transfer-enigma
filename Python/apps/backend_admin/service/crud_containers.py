from typing import Any

from backend_admin.schemas.data_browser import ContainerCreate, ContainerPatch, ContainerResponse
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_data_internal.schemas import ContainerModel, ContainerType


class CRUDContainer(CRUDBase):
    model = ContainerModel
    create_schema = ContainerCreate
    update_schema = ContainerCreate
    patch_schema = ContainerPatch
    response_schema = ContainerResponse
    list_filters = [
        FilterDef("size", "size", "eq"),
        FilterDef("weight_from", "weight_from", "gte"),
        FilterDef("weight_to", "weight_to", "lte"),
    ]

    def _build_instance(self, data: ContainerCreate) -> ContainerModel:
        return ContainerModel(
            size=data.size,
            weight_from=data.weight_from,
            weight_to=data.weight_to,
            name=data.name.strip(),
            type=ContainerType(data.type),
        )

    def _apply_update(self, model: ContainerModel, data: ContainerCreate) -> None:
        model.size = data.size
        model.weight_from = data.weight_from
        model.weight_to = data.weight_to
        model.name = data.name.strip()
        model.type = ContainerType(data.type)

    def _apply_patch(self, model: ContainerModel, data: ContainerPatch) -> None:
        if data.size is not None:
            model.size = data.size
        if data.weight_from is not None:
            model.weight_from = data.weight_from
        if data.weight_to is not None:
            model.weight_to = data.weight_to
        if data.name is not None:
            model.name = data.name.strip()
        if data.type is not None:
            model.type = ContainerType(data.type)

    def _apply_list_filters(self, stmt: Any, **filters: Any) -> Any:
        stmt = super()._apply_list_filters(stmt, **filters)
        type_filter = filters.get("type")
        if type_filter is not None and type_filter != "":
            stmt = stmt.where(ContainerModel.type == ContainerType(type_filter))
        return stmt


crud_containers = CRUDContainer()
