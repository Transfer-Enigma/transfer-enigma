from typing import Annotated

from fastapi import Depends

from fastapi_another_jwt_auth import AuthJWT

from ..config import Settings, get_settings


def request_auth(authorization: Annotated[AuthJWT, Depends()], settings: Annotated[Settings, Depends(get_settings)]):
    if not settings.DISABLE_ADMIN_AUTH_CHECK:
        authorization.jwt_required()
