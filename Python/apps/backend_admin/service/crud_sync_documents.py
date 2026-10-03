from backend_admin.schemas.data_browser import (
    SyncDocumentCreate,
    SyncDocumentPatch,
    SyncDocumentResponse,
)
from backend_admin.service.crud_base import CRUDBase, FilterDef
from backend_admin.service.routes_loading.documents import ROLE_COLUMNS
from module_shared.schemas.sync_document import SyncDocumentModel

_STR_FIELDS = ("title", "url", "file_name", *ROLE_COLUMNS, "uid_column")


class CRUDSyncDocument(CRUDBase):
    model = SyncDocumentModel
    create_schema = SyncDocumentCreate
    update_schema = SyncDocumentCreate
    patch_schema = SyncDocumentPatch
    response_schema = SyncDocumentResponse
    list_filters = [
        FilterDef("q", "title", "like"),
        FilterDef("source_type", "source_type", "eq"),
    ]

    def _strip(self, data: dict) -> dict:
        return {key: (value.strip() if key in _STR_FIELDS and isinstance(value, str) else value)
                for key, value in data.items()}

    def _build_instance(self, data: SyncDocumentCreate) -> SyncDocumentModel:
        return self.model(**self._strip(data.model_dump()))

    def _apply_update(self, model: SyncDocumentModel, data: SyncDocumentCreate) -> None:
        for key, value in self._strip(data.model_dump()).items():
            setattr(model, key, value)

    def _apply_patch(self, model: SyncDocumentModel, data: SyncDocumentPatch) -> None:
        for key, value in self._strip(data.model_dump(exclude_unset=True)).items():
            if value is not None:
                setattr(model, key, value)


crud_sync_documents = CRUDSyncDocument()
