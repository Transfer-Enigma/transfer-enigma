from entrypoints.admin.schemas.data_browser import (
    CachePolicyCreate,
    CachePolicyPatch,
    CachePolicyResponse,
)
from entrypoints.admin.service.crud_base import CRUDBase, FilterDef
from shared.orm.cache_policy import CachePolicyModel


class CRUDCachePolicies(CRUDBase):
    model = CachePolicyModel
    create_schema = CachePolicyCreate
    update_schema = CachePolicyCreate
    patch_schema = CachePolicyPatch
    response_schema = CachePolicyResponse
    list_filters = [
        FilterDef("source", "source", "like"),
        FilterDef("entity", "entity", "eq"),
    ]


crud_cache_policies = CRUDCachePolicies()
