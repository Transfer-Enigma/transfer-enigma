from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from fastapi_another_jwt_auth.exceptions import AuthJWTException


def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(status_code=HTTP_401_UNAUTHORIZED, content={"detail": exc.message})
