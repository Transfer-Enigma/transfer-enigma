<<<<<<<< HEAD:Python/apps/data/repositories/admin/crud_companies.py
from data.repositories.admin.crud_base import CRUDBase, FilterDef
from data.repositories.admin.schemas import CompanyCreate, CompanyPatch, CompanyResponse
from shared.orm.company import CompanyModel
========
from entrypoints.admin.schemas.data_browser import CompanyCreate, CompanyPatch, CompanyResponse
from entrypoints.admin.service.crud_base import CRUDBase, FilterDef
from shared.schemas.company import CompanyModel
>>>>>>>> 27ce1f08 (Python: Rename packages by architecture layer):Python/apps/entrypoints/admin/service/crud_companies.py


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
