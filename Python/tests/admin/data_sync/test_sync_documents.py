from fastapi import HTTPException

import pytest
from backend_admin.schemas.data_browser import SyncDocumentCreate, SyncDocumentPatch
from backend_admin.service.crud_sync_documents import crud_sync_documents
from backend_admin.service.routes_loading.documents import (
    document_not_found_error,
    list_documents,
    record_sync_status,
    record_validation_status,
    resolve_document,
    suggest_mapping,
)
from backend_admin.service.routes_loading.loading import synchronize
from backend_admin.service.routes_loading.sync_errors import SyncErrorCode
from sqlalchemy.ext.asyncio import AsyncSession

from .fixtures.frames import (
    clean_dropp_row,
    clean_sea_row,
    make_fc,
    make_frame,
    make_points_frame,
    make_services_frame,
)


def _doc_payload(**overrides):
    payload = {
        "title": "Main doc",
        "url": "https://docs.google.com/spreadsheets/d/abc",
        "sea_ws": "Море",
        "rail_ws": "ЖД",
        "dropp_ws": "Дропп",
    }
    payload.update(overrides)
    return SyncDocumentCreate(**payload)


def _clean_frames(fc):
    return {
        "sea": make_frame(fc, [clean_sea_row(fc)]),
        "rail": make_frame(fc, [clean_sea_row(fc, **{fc.effective_from: "2026-02-01"})]),
        "truck": None,
        "dropp": make_frame(fc, [clean_dropp_row(fc)]),
        "services": make_services_frame(fc),
        "points": make_points_frame(),
    }


class TestSyncDocumentCrud:
    async def test_create_applies_defaults(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(sqlite_session, _doc_payload())

        assert created.id is not None
        assert created.source_type == "gsheets"
        assert created.uid_column == "__uid"
        assert created.last_status is None
        assert created.last_errors_count == 0
        assert created.truck_ws is None

    async def test_get_update_patch_delete(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(sqlite_session, _doc_payload())

        fetched = await crud_sync_documents.get(sqlite_session, created.id)
        assert fetched.title == "Main doc"

        updated = await crud_sync_documents.update(
            sqlite_session, created.id, _doc_payload(title="Renamed", rail_ws=None),
        )
        assert updated.title == "Renamed"
        assert updated.rail_ws is None

        patched = await crud_sync_documents.patch(
            sqlite_session, created.id, SyncDocumentPatch(points_ws="Точки"),
        )
        assert patched.points_ws == "Точки"
        assert patched.title == "Renamed"

        await crud_sync_documents.delete(sqlite_session, created.id)
        await sqlite_session.flush()
        with pytest.raises(HTTPException) as exc_info:
            await crud_sync_documents.get(sqlite_session, created.id)
        assert exc_info.value.status_code == 404

    async def test_list_filters(self, sqlite_session: AsyncSession):
        await crud_sync_documents.create(sqlite_session, _doc_payload(title="Main"))
        await crud_sync_documents.create(
            sqlite_session, _doc_payload(title="File doc", source_type="file", file_name="data.xlsx"),
        )

        assert len(await crud_sync_documents.list(sqlite_session)) == 2
        assert len(await crud_sync_documents.list(sqlite_session, q="Main")) == 1
        assert len(await crud_sync_documents.list(sqlite_session, source_type="file")) == 1


class TestSuggestMapping:
    def test_russian_titles(self):
        assert suggest_mapping(["Морские перевозки", "ЖД", "ДРОПП", "Точки", "Услуги"]) == {
            "Морские перевозки": "sea_ws",
            "ЖД": "rail_ws",
            "ДРОПП": "dropp_ws",
            "Точки": "points_ws",
            "Услуги": "services_ws",
        }

    def test_english_titles(self):
        assert suggest_mapping(["sea routes", "Railway", "Truck", "drop-off"]) == {
            "sea routes": "sea_ws",
            "Railway": "rail_ws",
            "Truck": "truck_ws",
            "drop-off": "dropp_ws",
        }

    def test_unknown_titles_map_to_none(self):
        assert suggest_mapping(["README", "  "]) == {"README": None, "  ": None}

    def test_first_match_wins(self):
        assert suggest_mapping(["sea-drop"]) == {"sea-drop": "sea_ws"}


class TestResolveDocument:
    async def test_resolves_existing(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(sqlite_session, _doc_payload())
        resolved = await resolve_document(sqlite_session, created.id)
        assert resolved.url == "https://docs.google.com/spreadsheets/d/abc"

    async def test_missing_raises_coded_404(self, sqlite_session: AsyncSession):
        with pytest.raises(HTTPException) as exc_info:
            await resolve_document(sqlite_session, 999)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == SyncErrorCode.DOCUMENT_NOT_FOUND.value

    def test_helper_builds_coded_404(self):
        error = document_not_found_error(7)
        assert error.status_code == 404
        assert error.detail["code"] == "DOCUMENT_NOT_FOUND"

    async def test_list_documents_helper(self, sqlite_session: AsyncSession):
        await crud_sync_documents.create(sqlite_session, _doc_payload(title="A"))
        await crud_sync_documents.create(sqlite_session, _doc_payload(title="B"))
        documents = await list_documents(sqlite_session)
        assert [doc.title for doc in documents] == ["A", "B"]


class TestRecordStatus:
    async def test_validation_status(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(sqlite_session, _doc_payload())
        document = await resolve_document(sqlite_session, created.id)

        record_validation_status(document, 0)
        assert document.last_status == "validated"
        assert document.last_errors_count == 0

        record_validation_status(document, 3)
        assert document.last_status == "validation_failed"
        assert document.last_errors_count == 3
        assert document.loaded_at is None

    async def test_sync_status_sets_loaded_at_only_on_success(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(sqlite_session, _doc_payload())
        document = await resolve_document(sqlite_session, created.id)

        record_sync_status(document, False, 2)
        assert document.last_status == "failed"
        assert document.loaded_at is None

        record_sync_status(document, True, 1)
        assert document.last_status == "ok"
        assert document.last_errors_count == 1
        assert document.loaded_at is not None


class TestSynchronizeWithDocument:
    async def test_ok_run_records_status(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(sqlite_session, _doc_payload())
        document = await resolve_document(sqlite_session, created.id)
        fc = make_fc()

        outcome = await synchronize(sqlite_session, _clean_frames(fc), fc, document.url, True)
        record_sync_status(
            document, outcome.ok, len(outcome.report.errors) + len(outcome.report.warnings),
        )

        assert outcome.ok is True
        assert document.last_status == "ok"
        assert document.loaded_at is not None

    async def test_failed_gate_records_status(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(sqlite_session, _doc_payload())
        document = await resolve_document(sqlite_session, created.id)
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.container_transfer_terms: "XXX"})])

        outcome = await synchronize(sqlite_session, frames, fc, document.url, False)
        record_sync_status(
            document, outcome.ok, len(outcome.report.errors) + len(outcome.report.warnings),
        )

        assert outcome.ok is False
        assert document.last_status == "failed"
        assert document.last_errors_count > 0
        assert document.loaded_at is None

    async def test_document_mapping_drives_sync(self, sqlite_session: AsyncSession):
        created = await crud_sync_documents.create(
            sqlite_session, _doc_payload(sea_ws="Море", rail_ws=None, dropp_ws=None),
        )
        document = await resolve_document(sqlite_session, created.id)

        assert document.sea_ws == "Море"
        assert document.rail_ws is None
        assert document.dropp_ws is None
