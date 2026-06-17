from backend_admin.schemas.data_browser import RateCreate, RatePatch, RateResponse
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_shared.schemas.rate import RateModel


class CRUDRate(CRUDBase):
    model = RateModel
    create_schema = RateCreate
    update_schema = RateCreate
    patch_schema = RatePatch
    response_schema = RateResponse
    list_filters = [
        FilterDef("code", "code", "eq"),
        FilterDef("date", "date", "eq"),
    ]


crud_rates = CRUDRate()
