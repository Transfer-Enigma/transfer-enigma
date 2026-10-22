from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

from shared.dto.errors import NotFoundError, ResourcePermissionError, ValidationError


def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=HTTP_404_NOT_FOUND, content={"detail": str(exc)})


def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)})


def resource_permission_error_handler(request: Request, exc: ResourcePermissionError) -> JSONResponse:
    return JSONResponse(status_code=HTTP_403_FORBIDDEN, content={"detail": str(exc)})
