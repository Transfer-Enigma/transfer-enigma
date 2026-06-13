from typing import Any

from backend_admin.schemas.data_browser import ServiceCreate, ServicePatch, ServiceResponse
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_data_internal.schemas import ServiceModel


class CRUDService(CRUDBase):
    model = ServiceModel
    create_schema = ServiceCreate
    update_schema = ServiceCreate
    patch_schema = ServicePatch
    response_schema = ServiceResponse
    list_filters = [
        FilterDef("q", "name", "like"),
    ]

    def _apply_list_filters(self, stmt: Any, **filters: Any) -> Any:
        q = filters.get("q")
        if q:
            stmt = stmt.where(
                ServiceModel.name.like(f"%{q}%")
                | ServiceModel.internal_name.like(f"%{q}%")
            )
        return stmt


crud_services = CRUDService()
