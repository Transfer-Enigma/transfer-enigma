import datetime

from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from module_shared.schemas.sync_document import SyncDocumentModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .sync_errors import SyncErrorCode, get_message

ROLE_COLUMNS = ("sea_ws", "rail_ws", "truck_ws", "dropp_ws", "points_ws", "services_ws")

ROLE_KEYWORDS = (
    (("мор", "sea"), "sea_ws"),
    (("жд", "rail", "railway"), "rail_ws"),
    (("авто", "truck"), "truck_ws"),
    (("дроп", "drop"), "dropp_ws"),
    (("точк", "point", "город", "city"), "points_ws"),
    (("услуг", "service"), "services_ws"),
)


def suggest_mapping(worksheet_titles: list[str]) -> dict[str, str | None]:
    mapping = {}
    for title in worksheet_titles:
        normalized = title.strip().lower()
        mapping[title] = next(
            (column for keywords, column in ROLE_KEYWORDS if any(k in normalized for k in keywords)),
            None,
        )
    return mapping


def document_not_found_error(document_id: int) -> HTTPException:
    return HTTPException(
        status_code=HTTP_404_NOT_FOUND,
        detail={
            "code": SyncErrorCode.DOCUMENT_NOT_FOUND.value,
            "document": str(document_id),
            "detail": get_message(SyncErrorCode.DOCUMENT_NOT_FOUND, document=document_id),
        },
    )


async def resolve_document(db_session: AsyncSession, document_id: int) -> SyncDocumentModel:
    document = await db_session.get(SyncDocumentModel, document_id)
    if document is None:
        raise document_not_found_error(document_id)
    return document


async def list_documents(db_session: AsyncSession) -> list[SyncDocumentModel]:
    return list((await db_session.execute(
        select(SyncDocumentModel).order_by(SyncDocumentModel.id),
    )).scalars().all())


def record_validation_status(document: SyncDocumentModel, errors_count: int) -> None:
    document.last_status = "validated" if errors_count == 0 else "validation_failed"
    document.last_errors_count = errors_count


def record_sync_status(document: SyncDocumentModel, ok: bool, errors_count: int) -> None:
    document.last_status = "ok" if ok else "failed"
    document.last_errors_count = errors_count
    if ok:
        document.loaded_at = datetime.datetime.now(tz=datetime.UTC).replace(tzinfo=None)
