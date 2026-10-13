import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, File
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR

from backend_admin.dependencies.auth import request_auth
from backend_admin.responses import DetailErrorResponse, ErrorDescriptor, MultiErrorResponse
from backend_admin.responses_fabric import (
    create_an_error_descriptor_from_an_exception,
    create_multi_error_response_from_an_array_of_exceptions,
)
from backend_admin.service.db_management.db_dumper import create_db_dump
from backend_admin.service.db_management.db_eraser import clear_database_data
from backend_admin.service.db_management.db_loader import load_db_dump
from module_shared.database import Database, get_database

router = APIRouter(prefix="/db")


@router.get("/data", status_code=200, response_class=StreamingResponse, responses={
    HTTP_200_OK: {
        "content": {"application/octet-stream": {}},
        "description": "Database SQL Dump",
        "headers": {
            "Content-Disposition": {
                "description": "attachment; filename=\"dump-<today>.sql\"",
                "schema": {"type": "string"},
            },
        },
    },
    HTTP_500_INTERNAL_SERVER_ERROR: {"model": DetailErrorResponse[ErrorDescriptor]},
})
async def make_db_dump(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    structure: bool = True,
):
    async with db.session_context() as session:
        try:
            return StreamingResponse(
                create_db_dump(session, structure),
                headers={
                    "Content-Disposition": f"attachment; filename=\"dump-{datetime.date.today().isoformat()}.sql\"",
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_an_error_descriptor_from_an_exception(e),
            ) from e


@router.delete("/data", status_code=204, responses={
    HTTP_500_INTERNAL_SERVER_ERROR: {"model": DetailErrorResponse[ErrorDescriptor]},
})
async def erase_all_data(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        try:
            await clear_database_data(session)
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_an_error_descriptor_from_an_exception(e),
            ) from e


@router.post("/data", status_code=204, responses={
    HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": DetailErrorResponse[MultiErrorResponse],
        "description": "If any SQL query was failed or other error was occurred",
    },
})
async def load_dump(
    _: Annotated[None, Depends(request_auth)],
    dump_file: Annotated[bytes, File()],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        errors = await load_db_dump(session, dump_file.decode())

    if errors:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_multi_error_response_from_an_array_of_exceptions(errors),
        )
