from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.params import Depends, File

import gspread
from backend_admin.config import get_settings
from backend_admin.dependencies.auth import request_auth
from backend_admin.schemas.data_browser import (
    SyncDocumentCreate,
    SyncDocumentPatch,
    SyncDocumentResponse,
)
from backend_admin.service.crud_sync_documents import crud_sync_documents
from backend_admin.service.routes_loading.documents import suggest_mapping
from backend_admin.service.routes_loading.inputs import preview_upload
from module_shared.database import Database, get_database
from module_shared.resources import Resources

router = APIRouter(prefix="/db/sync-documents", tags=["sync-documents"])
settings = get_settings()


@router.get("", response_model=list[SyncDocumentResponse])
async def list_sync_documents(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    q: str = Query("", description="Search by title"),
    source_type: str = Query("", description="Filter by source type"),
):
    async with db.session_context() as session:
        return await crud_sync_documents.list(session, q=q, source_type=source_type)


@router.get("/sheets-preview")
async def preview_document_sheets(
    _: Annotated[None, Depends(request_auth)],
    url: str = Query(..., description="Google Sheets document URL"),
):
    gs = gspread.service_account(
        filename=Resources.get(settings.GOOGLE_SERVICE_ACCOUNT_RESOURCE_NAME, scope="backend_admin").path,
    )
    titles = [worksheet.title for worksheet in gs.open_by_url(url).worksheets()]
    return {"sheets": titles, "suggested_mapping": suggest_mapping(titles)}


@router.post("/preview-file")
async def preview_upload_file(
    _: Annotated[None, Depends(request_auth)],
    data_file: Annotated[bytes, File()],
):
    return preview_upload(data_file)


@router.get("/{document_id}", response_model=SyncDocumentResponse)
async def get_sync_document(
    document_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_sync_documents.get(session, document_id)


@router.post("", response_model=SyncDocumentResponse, status_code=201)
async def create_sync_document(
    payload: SyncDocumentCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_sync_documents.create(session, payload)


@router.put("/{document_id}", response_model=SyncDocumentResponse)
async def update_sync_document(
    document_id: int,
    payload: SyncDocumentCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_sync_documents.update(session, document_id, payload)


@router.patch("/{document_id}", response_model=SyncDocumentResponse)
async def patch_sync_document(
    document_id: int,
    payload: SyncDocumentPatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_sync_documents.patch(session, document_id, payload)


@router.delete("/{document_id}", status_code=204)
async def delete_sync_document(
    document_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_sync_documents.delete(session, document_id)
