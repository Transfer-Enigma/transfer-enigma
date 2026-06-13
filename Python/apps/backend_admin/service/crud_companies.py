from backend_admin.schemas.data_browser import CompanyCreate, CompanyPatch, CompanyResponse
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_data_internal.schemas import CompanyModel


class CRUDCompany(CRUDBase):
    model = CompanyModel
    create_schema = CompanyCreate
    update_schema = CompanyCreate
    patch_schema = CompanyPatch
    response_schema = CompanyResponse
    list_filters = [FilterDef("q", "name", "like")]

    def _build_instance(self, data: CompanyCreate) -> CompanyModel:
        return CompanyModel(name=data.name.strip())

    def _apply_update(self, model: CompanyModel, data: CompanyCreate) -> None:
        model.name = data.name.strip()

    def _apply_patch(self, model: CompanyModel, data: CompanyPatch) -> None:
        if data.name is not None:
            model.name = data.name.strip()


crud_companies = CRUDCompany()
